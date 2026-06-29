import networkx as nx
from core.logger import get_logger

logger = get_logger("knowledge_graph")


class KnowledgeGraph:
    """Directed graph of concept → relation → concept triples."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, concept: str):
        if concept:
            self.graph.add_node(concept.strip().lower())

    def add_edge(self, source: str, relation: str, target: str):
        if source and target:
            s, t = source.strip().lower(), target.strip().lower()
            self.graph.add_edge(s, t, relation=relation)

    def get_related(self, concept: str) -> list[dict]:
        key = concept.strip().lower()
        if key not in self.graph:
            return []
        return [
            {"target": nbr, "relation": self.graph[key][nbr].get("relation", "")}
            for nbr in self.graph.successors(key)
        ]

    def concepts(self) -> list[str]:
        return list(self.graph.nodes)
