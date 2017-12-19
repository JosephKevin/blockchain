import sys
import hashlib
import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib import parse as urlparse

class BlockChain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # genisis block
        self.new_block(previous_hash=1, proof=100)
        # set of nodes in the blockchain decentralized nw
        self.nodes = set()

    def register_node(self, address):
        """
        Function to add new node to list of nodes

        :param address: address of the node (string eg. 'http://192.168.0.5:5000')
        :return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def new_block(self, proof, previous_hash=None):
        """
        Function to create a new block

        :param proof: the proof given by the proof of work algorithm (int)
        :param previous_hash: the hash of the previous block (string)
        :return: created block
        """
        block = {'index': len(self.chain) +1,
                 'timestamp': time(),
                 'transactions': self.current_transactions,
                 'proof': proof,
                 'previous_hash': previous_hash or self.hash(self.chain[-1])}

        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next block

        :param sender: the address of the sender (string)
            recipient: the address of the recipient (string)
            amount: the amount to transfer

        Returns:
            The index of the block that will hold this transaction
        """
        block = {'sender': sender, 'recipient': recipient, 'amount': amount}
        self.current_transactions.append(block)
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        Function to convert a block to a SHA-256 hash

        :param block: the block (dictionary)

        :return: str: the hash sha-256 representation of the block (string)
        """
        # we need to sort the dictionary first before generating a SHA-256 key
        # because different arrangements of the dictionary k,v pairs give different
        # hashes
        block_str = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_str).hexdigest()


    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Function to give the proof of work
        POW is an algorithm that is difficult to find but easy to verify
        POW algorithm should give a number which satisfies the condition
        hash(last_proof, proof) = '0000....'


        :param last_proof: the last blocks proof (int)
        :return: proof: the value that satisfies the POW algorithm (int)
        """
        proof = 0
        while self.valid_proof(last_proof=last_proof, proof=proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Function to check if POW algorithm is satisfied

        :param last_proof:  the last blocks proof (int)
        :param proof: a number
        :return: True if the inputs satisfy the POW else False
        """
        guess = '{0}{1}'.format(last_proof, proof).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    def valid_chain(self, chain):
        """
        Function to check if a chain is a valid chain, to be a valid chain the proof and hash need to ful fill the
        block chain criteria
        :param chain: a blockchain (list)
        :return: A boolean True if the chain is valid else False
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print('{0}'.format(last_block))
            print('{0}'.format(block))
            print('\n-----------------------\n')
            # check if hash holds
            if self.hash(last_block) != block['previous_hash']:
                return False
            # check POW algorithm
            if not self.valid_proof(last_proof=last_block['proof'], proof=block['proof']):
                return False
            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        Function to resolve conflicts. Here we choose the longest blockchain as the valid chain
        :return: Boolean, True if our chain was replaced else False
        """
        neighbors = self.nodes
        new_chain = None
        max_length = len(self.chain)
        for node in neighbors:
            response = request.get('http://{0}/chain'.format(node))
            if response.status_code == 200:
                chain = response.json()['chain']
                length = response.json()['length']
            if length > max_length and self.valid_chain(chain=chain):
                max_length = length
                new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True
        return False


# Instantiate our node
app = Flask(__name__)

# get unique identifier for our node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the blockchain
blockchain = BlockChain()

@app.route('/mine', methods=['GET'])
def mine():
    """
    Function to run the POW algo to get a proof and , create a new block, add it to the chain and return the new block

    :return: the newly mined block
    """
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # create a new block
    # sender is set to 0 to signify that this node mined this block
    blockchain.new_transaction(sender='0', recipient=node_identifier, amount=1)

    # add the block to the blockchain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof=proof, previous_hash=previous_hash)

    response = {'message': 'New block forged',
                'index': block['index'],
                'transactions': block['transactions'],
                'proof': proof,
                'previous_hash': block['previous_hash']}

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing Value', 400

    index = blockchain.new_transaction(sender=values['sender'], recipient=values['recipient'], amount=values['amount'])

    response = {'message': 'Transaction will be added to block {0}'.format(index)}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return 'Please supply a valid list of nodes', 400
    for node in nodes:
        blockchain.register_node(node)
    response = {'message': 'New nodes have been successfully added',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaces:
        response = {'message': 'Our chain was replaced',
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'Our chain is autoritative',
                    'new_chain': blockchain.chain}
    return response, 201

if __name__ == '__main__':
    port = sys.argv[1]
    app.run(host='0.0.0.0', port=port)
