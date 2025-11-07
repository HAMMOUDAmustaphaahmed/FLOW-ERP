# models/blockchain.py
"""Modèles Blockchain - Version corrigée sans erreurs"""
from datetime import datetime
import hashlib
import json

class Blockchain:
    """Classe Blockchain complète et corrigée"""
    
    def __init__(self, difficulty=4):
        self.chain = []
        self.pending_transactions = []
        self.difficulty = difficulty
        self.nodes = set()
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Crée le bloc genesis"""
        genesis_block = {
            'index': 0,
            'timestamp': datetime.utcnow().isoformat(),
            'transactions': [{
                'type': 'genesis',
                'message': 'FlowERP Genesis Block',
                'created_at': datetime.utcnow().isoformat()
            }],
            'previous_hash': '0' * 64,
            'nonce': 0
        }
        genesis_block['hash'] = self.hash_block(genesis_block)
        self.chain.append(genesis_block)
    
    def hash_block(self, block):
        """Calcule le hash d'un bloc"""
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def add_transaction(self, transaction):
        """Ajoute une transaction à la liste d'attente"""
        transaction['timestamp'] = datetime.utcnow().isoformat()
        transaction['id'] = hashlib.sha256(
            json.dumps(transaction, sort_keys=True).encode()
        ).hexdigest()
        self.pending_transactions.append(transaction)
        return True
    
    def mine_pending_transactions(self, miner_address):
        """Mine les transactions en attente"""
        if not self.pending_transactions:
            return False
        
        # Créer un nouveau bloc avec les transactions en attente
        previous_block = self.chain[-1]
        new_block = {
            'index': len(self.chain),
            'timestamp': datetime.utcnow().isoformat(),
            'transactions': self.pending_transactions.copy(),
            'previous_hash': previous_block['hash'],
            'nonce': 0,
            'miner': miner_address
        }
        
        # Proof of Work
        new_block['hash'] = self.proof_of_work(new_block)
        
        # Ajouter le bloc à la chaîne
        self.chain.append(new_block)
        
        # Réinitialiser les transactions en attente
        self.pending_transactions = []
        
        return True
    
    def proof_of_work(self, block):
        """Effectue la preuve de travail"""
        block['nonce'] = 0
        computed_hash = self.hash_block(block)
        
        while not computed_hash.startswith('0' * self.difficulty):
            block['nonce'] += 1
            computed_hash = self.hash_block(block)
        
        return computed_hash
    
    def is_chain_valid(self):
        """Vérifie si la chaîne est valide"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Vérifier le hash du bloc actuel
            if current_block['hash'] != self.hash_block(current_block):
                return False
            
            # Vérifier le lien avec le bloc précédent
            if current_block['previous_hash'] != previous_block['hash']:
                return False
            
            # Vérifier la difficulté
            if not current_block['hash'].startswith('0' * self.difficulty):
                return False
        
        return True
    
    def get_latest_block(self):
        """Retourne le dernier bloc"""
        return self.chain[-1] if self.chain else None
    
    def get_chain(self):
        """Retourne toute la chaîne"""
        return self.chain
    
    def get_blockchain_stats(self):
        """Retourne les statistiques de la blockchain"""
        total_transactions = sum(
            len(block.get('transactions', []))
            for block in self.chain
        )
        
        latest_block = self.get_latest_block()
        
        return {
            'total_blocks': len(self.chain),
            'total_transactions': total_transactions,
            'pending_transactions': len(self.pending_transactions),
            'difficulty': self.difficulty,
            'nodes_count': len(self.nodes),
            'last_block_hash': latest_block['hash'] if latest_block else None,
            'last_block_time': latest_block['timestamp'] if latest_block else None,
            'is_valid': self.is_chain_valid()
        }
    
    def get_transaction_history(self, entity_type=None, entity_id=None):
        """Retourne l'historique des transactions pour une entité"""
        history = []
        for block in self.chain:
            for transaction in block.get('transactions', []):
                if entity_type and entity_id:
                    if (transaction.get('entity_type') == entity_type and 
                        str(transaction.get('entity_id')) == str(entity_id)):
                        history.append({
                            'block_index': block['index'],
                            'timestamp': block['timestamp'],
                            'transaction': transaction
                        })
                elif entity_type:
                    if transaction.get('entity_type') == entity_type:
                        history.append({
                            'block_index': block['index'],
                            'timestamp': block['timestamp'],
                            'transaction': transaction
                        })
                else:
                    history.append({
                        'block_index': block['index'],
                        'timestamp': block['timestamp'],
                        'transaction': transaction
                    })
        return history
    
    def add_node(self, node_address):
        """Ajoute un nœud au réseau"""
        self.nodes.add(node_address)
        return True
    
    def replace_chain(self, new_chain):
        """Remplace la chaîne actuelle si la nouvelle est plus longue et valide"""
        if len(new_chain) <= len(self.chain):
            return False
        
        temp_blockchain = Blockchain(self.difficulty)
        temp_blockchain.chain = new_chain
        
        if temp_blockchain.is_chain_valid():
            self.chain = new_chain
            return True
        
        return False