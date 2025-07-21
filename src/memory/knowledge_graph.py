class KnowledgeGraph:
    def __init__(self):
        self.nodes = []
        self.edges = []
    def add_node(self, node):
        self.nodes.append(node)
    def add_edge(self, from_node, to_node):
        self.edges.append((from_node, to_node)) 