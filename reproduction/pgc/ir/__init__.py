"""
Typed Probabilistic Graph Compiler: Intermediate Representations

Core IRs:
  - Evidence IR: immutable source material with provenance
  - Candidate IR: proposed entities, edges, schema changes
  - Decision IR: typed semantic questions posed to models
  - Constraint IR: formal invariants and validation rules
  - Mutation IR: proposed graph operations with preconditions/postconditions
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Any, Set, Tuple
from enum import Enum
from datetime import datetime
import json
import hashlib


class PrimitiveType(Enum):
    """Jev-style decision primitives."""
    NOUL = "noul"          # Probability of a yes/no proposition
    CHOICE = "choice"      # Select from enumerated alternatives
    SCORE = "score"        # Ordered rubric with distribution
    RULE = "rule"          # Deterministic constraint result
    GRAPH_MODEL = "graph_model"  # Graph-native model output


class ObjectKind(Enum):
    """What kind of graph object is proposed."""
    NODE = "node"
    EDGE = "edge"
    PROPERTY = "property"
    NODE_TYPE = "node_type"
    EDGE_TYPE = "edge_type"
    CONSTRAINT = "constraint"


class ConstraintStatus(Enum):
    """Validation outcome."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    UNKNOWN = "unknown"


class MutationStatus(Enum):
    """Stage in the mutation lifecycle."""
    PROPOSED = "proposed"
    EVIDENCE_SUPPORTED = "evidence_supported"
    CONSTRAINT_VALID = "constraint_valid"
    AUTO_COMMITTABLE = "auto_committable"
    REVIEW_REQUIRED = "review_required"
    COMMITTED = "committed"
    CONTESTED = "contested"
    SUPERSEDED = "superseded"


class MutationOperation(Enum):
    """Graph mutation operations."""
    CREATE_NODE = "create_node"
    CREATE_EDGE = "create_edge"
    MERGE_NODES = "merge_nodes"
    SET_PROPERTY = "set_property"
    ADD_TYPE = "add_type"
    ADD_NODE_TYPE = "add_node_type"
    ADD_EDGE_TYPE = "add_edge_type"
    ADD_PROPERTY = "add_property"
    ADD_CONSTRAINT = "add_constraint"
    RELAX_CONSTRAINT = "relax_constraint"
    DEPRECATE_TYPE = "deprecate_type"
    MIGRATE_INSTANCES = "migrate_instances"


# ============================================================================
# EVIDENCE IR: Immutable source material
# ============================================================================

@dataclass
class EvidenceSpan:
    """Location of evidence in a source document."""
    source_id: str
    source_version: str
    start_char: int
    end_char: int
    content: str  # actual text

    def content_hash(self) -> str:
        """Content fingerprint for integrity checking."""
        return hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class Evidence:
    """Immutable record of source material."""
    evidence_id: str
    source_id: str
    source_type: Literal["document", "database_record", "api_response"]
    source_version: str
    location: EvidenceSpan
    parser: str  # Which tool extracted this span
    parser_version: str
    observed_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.evidence_id, self.source_id, self.location.content_hash()))


# ============================================================================
# CANDIDATE IR: Proposals linked to evidence
# ============================================================================

@dataclass
class NodeCandidate:
    """Proposed graph node."""
    candidate_id: str
    kind: ObjectKind  # NODE or NODE_TYPE
    mention: str  # surface form or type name
    evidence: List[Evidence]

    # For entity nodes
    candidate_entities: Optional[List[Tuple[str, float]]] = None  # (entity_id, retrieval_score)
    candidate_properties: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)  # property: [(value, score), ...]
    candidate_types: List[Tuple[str, float]] = field(default_factory=list)  # (type_id, confidence)

    # For type/schema nodes
    type_name: Optional[str] = None
    type_properties: Optional[Dict[str, str]] = None  # property: datatype
    type_constraints: Optional[List[str]] = None

    temporal_validity: Optional[Tuple[Optional[str], Optional[str]]] = None  # (start, end) or (None, None) for atemporal


@dataclass
class EdgeCandidate:
    """Proposed graph edge."""
    candidate_id: str
    kind: ObjectKind  # EDGE or EDGE_TYPE
    subject_mention: str
    predicate_mention: str
    object_mention: str
    evidence: List[Evidence]

    # Resolution
    subject_candidates: Optional[List[Tuple[str, float]]] = None  # (entity_id, retrieval_score)
    predicate_candidates: List[Tuple[str, float]] = field(default_factory=list)  # (relation_id, confidence)
    object_candidates: Optional[List[Tuple[str, float]]] = None

    # For edge-type definitions
    edge_type_name: Optional[str] = None
    domain: Optional[str] = None  # Subject type constraint
    range_: Optional[str] = None  # Object type constraint

    temporal_validity: Optional[Tuple[Optional[str], Optional[str]]] = None

    # Explicit endpoint bindings, when resolution happened upstream.
    subject_id: Optional[str] = None
    object_id: Optional[str] = None


@dataclass
class PropertyCandidate:
    """Proposed property value."""
    candidate_id: str
    entity_id: str  # Which node
    property_name: str
    proposed_value: str
    evidence: List[Evidence]

    datatype: Optional[str] = None
    candidate_values: List[Tuple[str, float]] = field(default_factory=list)  # Alternatives


@dataclass
class CandidateGraphIR:
    """Container for all candidates from a source."""
    graph_id: str
    version: str
    timestamp: datetime

    nodes: List[NodeCandidate] = field(default_factory=list)
    edges: List[EdgeCandidate] = field(default_factory=list)
    properties: List[PropertyCandidate] = field(default_factory=list)


# ============================================================================
# DECISION IR: Typed semantic questions and their answers
# ============================================================================

@dataclass
class Decision:
    """Record of a semantic judgment."""
    decision_id: str
    primitive: PrimitiveType
    question: str

    # Model information
    model_family: str  # "jev", "llm", "classifier", "rule"
    model_version: str

    # Output
    distribution: Dict[str, float]  # Probability over outcomes

    # Optional fields
    model_params: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None  # Model's self-assessed confidence
    raw_output: Optional[Dict[str, Any]] = None  # Full model response

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    state_hash: Optional[str] = None  # Hash of input context

    # Relationships
    depends_on: List[str] = field(default_factory=list)  # decision_ids this depends on
    candidate_id: Optional[str] = None
    selected_outcome: Optional[str] = None
    request: Dict[str, Any] = field(default_factory=dict)
    execution_mode: str = "unknown"


@dataclass
class DecisionLedger:
    """Immutable record of all decisions."""
    ledger_id: str
    graph_id: str
    decisions: Dict[str, Decision] = field(default_factory=dict)

    def record(self, decision: Decision) -> None:
        """Add decision to ledger."""
        if decision.decision_id in self.decisions:
            raise ValueError(f"Decision {decision.decision_id} already recorded")
        self.decisions[decision.decision_id] = decision

    def by_model_version(self, model_version: str) -> List[Decision]:
        """Retrieve decisions from a specific model version."""
        return [d for d in self.decisions.values() if d.model_version == model_version]


# ============================================================================
# CONSTRAINT IR: Formal validation rules
# ============================================================================

@dataclass
class Constraint:
    """Validation rule."""
    constraint_id: str
    constraint_type: Literal["type", "cardinality", "referential", "uniqueness", "temporal", "logical"]
    description: str
    formal_spec: Any  # Declarative rule dict, or an explicitly supported shorthand.

    # Evaluation
    evaluated: bool = False
    status: ConstraintStatus = ConstraintStatus.UNKNOWN
    evidence: Optional[str] = None  # Why it passed/failed


@dataclass
class ConstraintSet:
    """Graph schema as formal constraints."""
    schema_id: str
    schema_version: str
    constraints: Dict[str, Constraint] = field(default_factory=dict)


# ============================================================================
# MUTATION IR: Proposed graph changes
# ============================================================================

@dataclass
class MutationPlan:
    """Staged graph mutation with full lineage."""
    mutation_id: str
    operation: MutationOperation

    # What is being changed
    target_entity: Optional[str] = None  # Entity ID if applicable
    target_entities: Optional[List[str]] = None  # For merge/migrate

    # The change
    new_properties: Dict[str, Any] = field(default_factory=dict)
    new_type: Optional[str] = None

    # Correctness
    preconditions: List[str] = field(default_factory=list)  # "target_exists", "not_already_merged"
    postconditions: List[str] = field(default_factory=list)  # "entity has type X"

    # Justification
    evidence_links: List[Evidence] = field(default_factory=list)
    decision_links: List[str] = field(default_factory=list)  # decision_ids
    candidate_link: Optional[str] = None  # candidate_id

    # Reversibility
    inverse_operation: Optional['MutationPlan'] = None

    # Lifecycle
    status: MutationStatus = MutationStatus.PROPOSED
    constraint_results: Dict[str, ConstraintStatus] = field(default_factory=dict)

    # Audit trail
    proposed_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    committed_at: Optional[datetime] = None
    committed_by: Optional[str] = None
    graph_version_at_commit: Optional[str] = None

    # Risk assessment
    risk_class: Literal["low", "medium", "high"] = "medium"
    requires_review: bool = False
    subject_id: Optional[str] = None
    predicate: Optional[str] = None
    object_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # prerequisite mutation IDs
    selected_outcome: Optional[str] = None


@dataclass
class Transaction:
    """Atomic commit of mutations."""
    transaction_id: str
    graph_id: str
    graph_version_before: str
    graph_version_after: str

    mutations: List[MutationPlan] = field(default_factory=list)
    committed_at: Optional[datetime] = None
    committed_by: str = "system"

    read_set: Set[str] = field(default_factory=set)  # Entities that were checked
    affected_set: Set[str] = field(default_factory=set)  # Entities that were modified
    status: str = "proposed"
    errors: List[str] = field(default_factory=list)
    fingerprint: Optional[str] = None
    certificate: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# PROVENANCE IR: Causal links (PROV-O compatible)
# ============================================================================

@dataclass
class ProvenanceEntry:
    """Why does a fact exist? Full causal chain."""
    entity_id: str  # The entity or edge
    entity_kind: ObjectKind

    # Origin
    evidence: List[Evidence]
    candidate_id: Optional[str]

    # Processing
    decisions: List[Decision]
    constraints_checked: List[Constraint]

    # Materialization
    mutation_id: Optional[str]
    transaction_id: Optional[str]
    graph_version: str

    # History
    created_at: datetime
    superseded_by: Optional[str] = None  # If this fact was replaced
    contested: bool = False


# ============================================================================
# Serialization helpers
# ============================================================================

def evidence_span_to_dict(span: EvidenceSpan) -> Dict:
    return {
        "source_id": span.source_id,
        "source_version": span.source_version,
        "start_char": span.start_char,
        "end_char": span.end_char,
        "content": span.content,
    }


def decision_to_dict(decision: Decision) -> Dict:
    return {
        "decision_id": decision.decision_id,
        "primitive": decision.primitive.value,
        "question": decision.question,
        "model_family": decision.model_family,
        "model_version": decision.model_version,
        "distribution": decision.distribution,
        "confidence": decision.confidence,
        "timestamp": decision.timestamp.isoformat(),
        "depends_on": decision.depends_on,
    }
