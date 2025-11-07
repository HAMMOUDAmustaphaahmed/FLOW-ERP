import requests
import threading
import time
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BlockchainSyncManager:
    """Gestionnaire de synchronisation de la blockchain entre nœuds"""
    
    def __init__(self, blockchain, sync_interval: int = 300):
        """
        Args:
            blockchain: Instance de la blockchain
            sync_interval: Intervalle de synchronisation en secondes (défaut: 5 minutes)
        """
        self.blockchain = blockchain
        self.sync_interval = sync_interval
        self.is_running = False
        self.sync_thread = None
        self.nodes = set()
    
    def register_node(self, node_url: str):
        """Enregistre un nouveau nœud dans le réseau"""
        if node_url and node_url not in self.nodes:
            self.nodes.add(node_url)
            self.blockchain.add_node(node_url)
            logger.info(f"Nœud enregistré: {node_url}")
            return True
        return False
    
    def unregister_node(self, node_url: str):
        """Désenregistre un nœud du réseau"""
        if node_url in self.nodes:
            self.nodes.remove(node_url)
            logger.info(f"Nœud désenregistré: {node_url}")
            return True
        return False
    
    def get_chain_from_node(self, node_url: str) -> Dict[str, Any]:
        """Récupère la blockchain d'un nœud"""
        try:
            response = requests.get(
                f"{node_url}/api/blockchain/chain",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération de la chaîne depuis {node_url}: {e}")
        return None
    
    def sync_with_nodes(self):
        """Synchronise avec tous les nœuds enregistrés"""
        if not self.nodes:
            logger.info("Aucun nœud enregistré pour la synchronisation")
            return False
        
        logger.info(f"Début de la synchronisation avec {len(self.nodes)} nœuds")
        
        longest_chain = None
        max_length = len(self.blockchain.chain)
        
        # Parcourir tous les nœuds
        for node in self.nodes:
            try:
                chain_data = self.get_chain_from_node(node)
                
                if chain_data:
                    length = chain_data.get('length', 0)
                    chain = chain_data.get('chain', [])
                    
                    # Vérifier si cette chaîne est plus longue
                    if length > max_length:
                        logger.info(f"Chaîne plus longue trouvée sur {node}: {length} blocs")
                        longest_chain = chain
                        max_length = length
            
            except Exception as e:
                logger.error(f"Erreur lors de la synchronisation avec {node}: {e}")
                continue
        
        # Remplacer notre chaîne si une plus longue est trouvée
        if longest_chain:
            if self.blockchain.replace_chain(longest_chain):
                logger.info(f"Blockchain remplacée par une chaîne de {max_length} blocs")
                return True
            else:
                logger.warning("La nouvelle chaîne n'est pas valide, conservation de la chaîne actuelle")
        else:
            logger.info("Notre chaîne est à jour")
        
        return False
    
    def broadcast_new_block(self, block: Dict[str, Any]):
        """Diffuse un nouveau bloc à tous les nœuds"""
        if not self.nodes:
            return
        
        logger.info(f"Diffusion du bloc {block.get('index')} à {len(self.nodes)} nœuds")
        
        for node in self.nodes:
            try:
                requests.post(
                    f"{node}/api/blockchain/new-block",
                    json={'block': block},
                    timeout=5
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur lors de la diffusion au nœud {node}: {e}")
    
    def broadcast_transaction(self, transaction: Dict[str, Any]):
        """Diffuse une nouvelle transaction à tous les nœuds"""
        if not self.nodes:
            return
        
        logger.info(f"Diffusion de la transaction à {len(self.nodes)} nœuds")
        
        for node in self.nodes:
            try:
                requests.post(
                    f"{node}/api/blockchain/new-transaction",
                    json={'transaction': transaction},
                    timeout=5
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur lors de la diffusion au nœud {node}: {e}")
    
    def _sync_loop(self):
        """Boucle de synchronisation automatique"""
        while self.is_running:
            try:
                self.sync_with_nodes()
            except Exception as e:
                logger.error(f"Erreur dans la boucle de synchronisation: {e}")
            
            # Attendre l'intervalle avant la prochaine synchronisation
            time.sleep(self.sync_interval)
    
    def start_auto_sync(self):
        """Démarre la synchronisation automatique"""
        if self.is_running:
            logger.warning("La synchronisation automatique est déjà en cours")
            return
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info(f"Synchronisation automatique démarrée (intervalle: {self.sync_interval}s)")
    
    def stop_auto_sync(self):
        """Arrête la synchronisation automatique"""
        if not self.is_running:
            logger.warning("La synchronisation automatique n'est pas en cours")
            return
        
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=10)
        logger.info("Synchronisation automatique arrêtée")
    
    def get_network_status(self) -> Dict[str, Any]:
        """Récupère le statut du réseau"""
        active_nodes = []
        inactive_nodes = []
        
        for node in self.nodes:
            try:
                response = requests.get(
                    f"{node}/api/blockchain/stats",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    active_nodes.append({
                        'url': node,
                        'total_blocks': data.get('total_blocks'),
                        'is_valid': data.get('is_valid')
                    })
                else:
                    inactive_nodes.append(node)
            except requests.exceptions.RequestException:
                inactive_nodes.append(node)
        
        return {
            'total_nodes': len(self.nodes),
            'active_nodes': len(active_nodes),
            'inactive_nodes': len(inactive_nodes),
            'nodes_details': active_nodes,
            'inactive_nodes_list': inactive_nodes,
            'sync_running': self.is_running,
            'local_chain_length': len(self.blockchain.chain)
        }


# Routes API pour la synchronisation blockchain
def register_sync_routes(app, sync_manager):
    """Enregistre les routes API pour la synchronisation"""
    from flask import jsonify, request
    
    @app.route('/api/blockchain/nodes/register', methods=['POST'])
    def register_node():
        """Enregistrer un nouveau nœud"""
        data = request.get_json()
        node_url = data.get('node_url')
        
        if not node_url:
            return jsonify({'error': 'node_url requis'}), 400
        
        if sync_manager.register_node(node_url):
            return jsonify({
                'success': True,
                'message': f'Nœud {node_url} enregistré',
                'total_nodes': len(sync_manager.nodes)
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Nœud déjà enregistré'
            }), 400
    
    @app.route('/api/blockchain/nodes/list', methods=['GET'])
    def list_nodes():
        """Lister tous les nœuds"""
        return jsonify({
            'success': True,
            'nodes': list(sync_manager.nodes),
            'count': len(sync_manager.nodes)
        }), 200
    
    @app.route('/api/blockchain/nodes/unregister', methods=['POST'])
    def unregister_node():
        """Désenregistrer un nœud"""
        data = request.get_json()
        node_url = data.get('node_url')
        
        if not node_url:
            return jsonify({'error': 'node_url requis'}), 400
        
        if sync_manager.unregister_node(node_url):
            return jsonify({
                'success': True,
                'message': f'Nœud {node_url} désenregistré'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Nœud non trouvé'
            }), 404
    
    @app.route('/api/blockchain/sync', methods=['POST'])
    def manual_sync():
        """Synchronisation manuelle"""
        success = sync_manager.sync_with_nodes()
        return jsonify({
            'success': success,
            'message': 'Synchronisation effectuée' if success else 'Aucune mise à jour nécessaire',
            'chain_length': len(sync_manager.blockchain.chain)
        }), 200
    
    @app.route('/api/blockchain/network/status', methods=['GET'])
    def network_status():
        """Statut du réseau"""
        status = sync_manager.get_network_status()
        return jsonify({
            'success': True,
            'status': status
        }), 200
    
    @app.route('/api/blockchain/new-block', methods=['POST'])
    def receive_new_block():
        """Reçoit un nouveau bloc d'un autre nœud"""
        data = request.get_json()
        block_data = data.get('block')
        
        if not block_data:
            return jsonify({'error': 'Données de bloc manquantes'}), 400
        
        # Vérifier et ajouter le bloc
        # Note: Implémentation simplifiée, dans un cas réel il faudrait
        # valider le bloc avant de l'ajouter
        return jsonify({
            'success': True,
            'message': 'Bloc reçu'
        }), 200
    
    @app.route('/api/blockchain/new-transaction', methods=['POST'])
    def receive_new_transaction():
        """Reçoit une nouvelle transaction d'un autre nœud"""
        data = request.get_json()
        transaction = data.get('transaction')
        
        if not transaction:
            return jsonify({'error': 'Données de transaction manquantes'}), 400
        
        sync_manager.blockchain.add_transaction(transaction)
        
        return jsonify({
            'success': True,
            'message': 'Transaction ajoutée'
        }), 200