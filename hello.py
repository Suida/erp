from collections import defaultdict
from typing import List, Tuple, Callable

import graphviz


class EntityFields:
    def __init__(self, fields: List[str]):
        self._fields = set(fields)

    def _foreign_to()


class Entity:
    HEADER_BGCOLOR = '#cfcfcf'
    HEADER_MIN_WIDTH = '72'
    HEADER_CELL_PADDING = '5'

    FIELD_ALIGN = 'left'
    FIELD_MIN_WIDTH = '56'

    HEADER_TPLT = '\t<tr><td {attrs}>{field_name}</td></tr>'
    ROW_TPLT = '\t<tr><td {attrs} port="{field_name}">  {field_name}</td></tr>'
    TABLE_TPLT = '<table border="1" cellborder="0" cellspacing="0" cellpadding="2">{rows}</table>'

    PRIMARY_KEY_IDENTIFIER = 'ID'
    FOREIGN_KEY_IDENTIFIER = 'idx'

    def __init__(self, tablename: str, fields: List[str] = None):
        """
        fields:
            ```
            ['id', 'name', 'age', ...]
            ```
        """
        self._tablename = tablename
        self._fields = [f.lower() for f in fields] if fields else []
        if 'id' not in self.fields:
            self.fields.insert(0, 'id')

        self._html = None
        self._edges = []

    def _get_header(self) -> str:
        """Get table header according to table name"""
        attrs = ''
        attr_map = {
            'bgcolor': self.HEADER_BGCOLOR,
            'width': self.HEADER_MIN_WIDTH,
            'cellpadding': self.HEADER_CELL_PADDING,
        }
        for k, v in attr_map.items():
            attrs += f'{k}="{v}" '
        return self.HEADER_TPLT.format(attrs=attrs, field_name=self.tablename.capitalize())

    def _get_row(self, field: str) -> str:
        attrs = ''
        attr_map = {
            'align': self.FIELD_ALIGN,
        }
        for k, v in attr_map.items():
            attrs += f'{k}="{v}" '
        return self.ROW_TPLT.format(attrs=attrs, field_name=field)

    def _get_table(self, hdr: str, rows: str) -> str:
        rows = '\n'.join(['', hdr, *rows, ''])
        return self.TABLE_TPLT.format(rows=rows)

    def _update_html(self) -> str:
        assert self.fields is not None
        hdr = self._get_header()
        rows = [self._get_row(field) for field in self.fields]
        self._html = self._get_table(hdr, rows)
        return self._html

    def edge_to(self, ent, self_port=None):
        self._edges.append((self, ent, self_port))

    @property
    def tablename(self):
        return self._tablename

    @property
    def fields(self):
        return self._fields[:]

    @property
    def node_name(self) -> str:
        return self.tablename

    @property
    def label(self) -> str:
        return '<' + (self._html or self._update_html()) + '>'

    @property
    def edges(self) -> List[Tuple['Entity', 'Entity', str]]:
        return self._edges

    def __getattribute__(self, name: str, /):
        if name.startswith('port_') and name[5:] in self.fields:
            return '{}:{}'.format(self.tablename, name[5:])
        elif name == 'port':
            return self.tablename
        return super().__getattribute__(name)

class ERGraph(graphviz.Digraph):
    """
    Usage:
        >>> person = Entity('person', ['id', 'name', 'age', 'gender',])
        >>> er = ERGraph(nodes=[person])
        >>> student = Entity('student', ['id', 'school', 'class', 'score', 'person_id'])
        >>> er.node(student)
        >>> er.edge(student.port_person_id, person)
        >>> er
    """
    def __init__(self, *args, nodes, **kwargs):
        super().__init__(*args, **kwargs)
        self.attr('node', shape='plaintext', fontname='Cascadia Code', fontsize='10')

        self.entities = set()
        self._linked_edges = set()
        self._promised_edges = defaultdict(lambda : [])

        assert isinstance(nodes, list)
        for ent in nodes:
            self.node(ent)

    def node(self, ent: Entity, *args, **kwargs):
        assert isinstance(ent, Entity), type(ent) + "is not instance of Entity"
        super().node(ent.node_name, ent.label, *args, **kwargs)
        self.entities.add(ent)
        [f() for f in self._promised_edges.pop(ent, [])]
        for edge in ent.edges:
            self._add_edge(*edge)

    def edge(
        self,
        src_ent: Entity,
        dst_ent: Entity,
        src_port: str = None,
        *args,
        **kwargs
    ):
        """Create an edge between owned entities"""
        assert src_ent in self.entities
        assert dst_ent in self.entities
        return self._add_edge(src_ent, dst_ent, src_port, *args, **kwargs)

    def _add_edge(
        self,
        src_ent: Entity,
        dst_ent: Entity,
        src_port: str = None,
        *args,
        **kwargs
    ):
        """Create an edge or create edge creation closure

        Between owned entities, creation is directly performed. When there is
        one entity not owned, the creation operation is closured and stored, and
        once the missing entity is added, the closure will be executed.
        """
        src = getattr(src_ent, 'port_'+src_port) if src_port else src_ent.port
        dst = dst_ent.port

        if (src, dst) in self._linked_edges:
            # Duplicated edges are not allowed
            return

        def promised_edge():
            graphviz.Digraph.edge(self, src, dst, *args, **kwargs)
            self._linked_edges.add((src, dst))

        # There must be at least one node being added into `self.entities`
        if src_ent not in self.entities:
            self._promised_edges[src_ent].append(promised_edge)
        elif dst_ent not in self.entities:
            self._promised_edges[dst_ent].append(promised_edge)
        else:
            promised_edge()
