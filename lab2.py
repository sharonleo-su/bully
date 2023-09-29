import selectors
import socket
import pickle
from enum import Enum
from selectors import DefaultSelector
from datetime import datetime
import time

BUF_SZ = 1024
ASSUME_FAILURE_TIMEOUT = 0.5
CHECK_INTERVAL = 20
GCD_HOST = '127.0.0.1'
GCD_PORT = 23700


class State(Enum):
    """
    Enumeration of states a peer can be in for the Lab2 class.
    """
    QUIESCENT = 'QUIESCENT'  # Erase any memory of this peer

    # Outgoing message is pending
    SEND_ELECTION = 'ELECTION'
    SEND_VICTORY = 'COORDINATOR'
    SEND_OK = 'OK'

    # Incoming message is pending
    WAITING_FOR_OK = 'WAIT_OK'  # When I've sent them an ELECTION message.
    WAITING_FOR_VICTOR = 'WHO IS THE WINNER?'  # This only applies to myself
    WAITING_FOR_ANY_MESSAGE = 'WAITING'  # When I've done an accept on their connect to my server.

    def is_incoming(self):
        """Categorization helper."""
        return self not in (State.SEND_ELECTION, State.SEND_VICTORY, State.SEND_OK)


class Lab2(object):

    def __init__(self, gcd_address, next_birthday, su_id):
        """
        Constructs a Lab2 object to talk to the given GCD
        """
        self.gcd_address = (gcd_address[0], int(gcd_address[1]))
        self.days_to_birthday = (next_birthday - datetime.now()).days
        self.pid = (self.days_to_birthday, int(su_id))
        self.members = {}
        self.states = {}
        self.bully = None
        self.selector = DefaultSelector()
        self.listener, self.listener_address = self.start_a_server()

    def start_a_server(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind(('localhost', 0))
        print('Listening on {}'.format(lsock.getsockname()))
        lsock.listen()
        lsock.setblocking(False)
        self.selector.register(lsock, selectors.EVENT_READ, data=None)
        return lsock, lsock.getsockname()[1]

    def run(self):
        self.join_group()
        self.start_election(reason='Starting election after joining group')
        # print('REGISTERED SOCKETS: {}'.format(self.selector.get_map()))
        while True:
            events = self.selector.select(CHECK_INTERVAL)
            # print('SELECTED EVENT: {}'.format(events))
            for key, mask in events:
                sock = key.fileobj
                print('KEY FILEOBJ TYPE: {}'.format(sock))
                if key.fileobj == self.listener:
                    self.accept_peer()
                if mask & selectors.EVENT_READ and key.data is not None:
                    response = sock.recv(BUF_SZ)
                    print('RESPONSE IN RUN: {}'.format(response))
                    # self.receive(key.fileobj)
                if mask & selectors.EVENT_WRITE and key.data is not None:
                    sock.send(key.data)
                    # self.send(key.fileobj)

    def accept_peer(self):
        peer_socket, address = self.listener.accept()
        peer_socket.setblocking(False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.selector.register(peer_socket, events, data=None)
        for pid, peer_address in self.members.items():
            if peer_address == peer_socket.getpeername():
                self.set_state(State.WAITING_FOR_ANY_MESSAGE, peer=(pid, peer_address), switch_mode=True)

    def send_message(self, peer):
        state = self.get_state(peer)
        peer_socket = None
        try:
            peer_socket = self.send(peer=peer, message_name=state.value, message_data=pickle.dumps(self.members))
        except ConnectionError as err:
            print('Could not connect to peer: {}'.format(err))
        except Exception:
            pass

        if state == State.SEND_ELECTION:
            self.set_state(State.WAITING_FOR_OK, peer, switch_mode=True)
        else:
            self.set_quiescent(peer)
        return peer_socket

    def receive_message(self, peer_socket):
        peer = peer_socket.getsockname()[1]
        state = self.get_state(peer)
        response = None
        try:
            response = self.receive(peer_socket)
        except Exception as err:
            print('Something went wrong: {}'.format(err))
            print('No response from peer: setting QUIESCENT')
            self.set_state(State.QUIESCENT, peer, switch_mode=True)
        if not response:
            self.set_state(State.QUIESCENT, peer, switch_mode=True)
        print('Received response: {}'.format(response))
        # If response is OK or something else, deal with it.
        if response is not None:
            if response[0] == State.SEND_OK:
                self.set_state(State.QUIESCENT, (self.pid, self.listener_address), switch_mode=True)
            if state == State.WAITING_FOR_OK:
                if response[0] != State.SEND_OK:
                    self.set_state(State.QUIESCENT, peer, switch_mode=True)
        print('State of peer: {} is {}'.format(peer, self.get_state(peer)))
        return response

    def get_leader(self):
        if self.bully is None:
            print('Leader is unknown')
        else:
            print('Leader is {}'.format(self.bully))

    def get_state(self, peer=None, detail=False):
        """
        Look up current state in state table.
        :param peer: socket connected to peer process(None means self)
        :param detail: if True, then the state and timestamp are both returned
        :return: either the state or (state, timestamp) depending on detail (not found gives (QUIESCENT, None))
        """
        if peer is None:
            peer = (self.pid, self.listener_address)
        if peer not in self.states:
            self.set_quiescent(peer)
        return self.states[peer]  # if detail else status[0]

    def set_state(self, state, peer=None, switch_mode=False):
        if peer is None:
            peer = (self.pid, self.listener_address)
        self.states[peer] = state

    def set_quiescent(self, peer=None):
        if peer is None:
            peer = (self.pid, self.listener_address)
        self.states[peer] = State.QUIESCENT

    def start_election(self, reason):
        """
        Send ELECTION message to all potential leaders
        """
        self.get_leader()
        print('Starting election after joining group.')
        potential_leaders = {}
        for pid, peer_address in self.members.items():
            if pid[0] > self.pid[0]:
                potential_leaders[pid] = peer_address
            elif pid[0] == self.pid[0]:
                if pid[1] > self.pid[1]:
                    potential_leaders[pid] = peer_address
        print('Potential leaders: {}'.format(potential_leaders))
        if not potential_leaders:
            for pid, address in self.members:
                self.states[(pid, address)] = State.SEND_VICTORY
                self.send_message((pid, address))
        else:
            for pid, address in potential_leaders.items():
                self.states[(pid, address)] = State.SEND_ELECTION
                peer_socket = self.send_message((pid, address))
                response = self.receive_message(peer_socket)
                print('Response: {}'.format(response))
        print('End of election messages ...')

        found_leader = False
        for peer, state in self.states.items():
            if state != State.QUIESCENT:
                found_leader = True
                break

        if not found_leader:
            self.declare_victory('All peers quiescent.')

    def declare_victory(self, reason):
        print('Sending COORDINATOR message to all members: {}'.format(reason))
        for pid, address in self.members.items():
            self.set_state(State.SEND_VICTORY, (pid, address), switch_mode=True)
            self.send_message((pid, address))
            self.bully = 'self'
            self.get_leader()

    def update_members(self, their_idea_of_membership):
        for pid, address in their_idea_of_membership.items():
            if pid not in self.members:
                self.members[pid] = address
        print('Updated list of members: {}'.format(self.members))

    def send(self, peer, message_name, message_data=None, wait_for_reply=False, buffer_size=BUF_SZ):
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.setblocking(False)
        peer_socket.connect_ex(peer[1])
        self.selector.register(peer_socket, selectors.EVENT_WRITE, data=pickle.dumps((message_name, message_data)))
        return peer_socket

    def receive(self, peer, buffer_size=BUF_SZ):
        self.selector.register(peer, selectors.EVENT_READ, data=None)
        # response = pickle.loads(peer.recv(buffer_size))
        # if response[1]:
        #     new_members = response[1]
        #     self.update_members(new_members)
        # print('Received response {} from {}'.format(response, peer))

    def join_group(self):
        print('Joining group of peers')
        gcd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with gcd_socket:
            gcd_socket.connect((self.gcd_address[0], self.gcd_address[1]))
            message_name = 'JOIN'
            message_data = (self.pid, self.listener.getsockname())
            gcd_socket.sendall(pickle.dumps((message_name, message_data)))
            self.members = pickle.loads(gcd_socket.recv(BUF_SZ))
            print('Response from GCD: {}'.format(self.members))

    @staticmethod
    def pr_now():
        pass


if __name__ == '__main__':
    my_node = Lab2(gcd_address=[GCD_HOST, GCD_PORT],
                   next_birthday=datetime.strptime('08-31-2023 00:00:00', '%m-%d-%Y %H:%M:%S'),
                   su_id='4181858')
    my_node.run()
