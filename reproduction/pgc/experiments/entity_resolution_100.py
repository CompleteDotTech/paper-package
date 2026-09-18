"""
Entity-Resolution 100: Hand-curated entity-resolution examples for Week 5-6 experiments.

This module provides 100 entity-matching examples spanning:
  - Person names (with variations, abbreviations, language variants)
  - Organizations (abbreviations, legal vs. common names)
  - Proteins (scientific names vs. abbreviations)
  - Chemical compounds (IUPAC names vs. common names)

Usage:
    examples = load_entity_resolution_100()
    for ex in examples:
        print(f"{ex.mention_1:30} → {ex.mention_2:30} : {ex.gold_label}")
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ERExample:
    """Entity-resolution example."""
    example_id: str
    mention_1: str
    mention_2: str
    gold_label: str  # "same" | "different" | "uncertain"
    context: Optional[str] = None
    category: Optional[str] = None  # "person" | "org" | "protein" | "compound"


def load_entity_resolution_100() -> List[ERExample]:
    """Load 100 entity-resolution examples."""

    examples = []

    # ========================================================================
    # Category 1: Person Names (25 examples)
    # ========================================================================

    person_examples = [
        # Same person - variations
        ERExample(
            example_id="er_person_001",
            mention_1="Jane Smith",
            mention_2="J. Smith",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_002",
            mention_1="John Michael Anderson",
            mention_2="J. M. Anderson",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_003",
            mention_1="Robert Johnson",
            mention_2="Bob Johnson",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_004",
            mention_1="Elisabeth Mueller",
            mention_2="Elizabeth Müller",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_005",
            mention_1="Antonio Garcia Lopez",
            mention_2="A. G. Lopez",
            gold_label="same",
            category="person"
        ),
        # Different people - similar names
        ERExample(
            example_id="er_person_006",
            mention_1="John Smith",
            mention_2="John Smiths",
            gold_label="different",
            category="person"
        ),
        ERExample(
            example_id="er_person_007",
            mention_1="Michael Brown",
            mention_2="Michael Browne",
            gold_label="different",
            category="person"
        ),
        ERExample(
            example_id="er_person_008",
            mention_1="Mary Jones",
            mention_2="Maria Jones",
            gold_label="uncertain",
            category="person"
        ),
        ERExample(
            example_id="er_person_009",
            mention_1="Sarah Williams",
            mention_2="Sara Williams",
            gold_label="uncertain",
            category="person"
        ),
        ERExample(
            example_id="er_person_010",
            mention_1="David Lee",
            mention_2="David Li",
            gold_label="uncertain",
            category="person"
        ),
        ERExample(
            example_id="er_person_011",
            mention_1="James Robert Wilson",
            mention_2="J. R. Wilson",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_012",
            mention_1="Catherine Mary O'Brien",
            mention_2="C. M. O'Brien",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_013",
            mention_1="Peter Thompson",
            mention_2="Pete Thompson",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_014",
            mention_1="Alexander Kozlov",
            mention_2="Aleksandr Kozlov",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_015",
            mention_1="Margaret Mary",
            mention_2="Maggie Mary",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_016",
            mention_1="Daniel Garcia",
            mention_2="Daniel Garcea",
            gold_label="different",
            category="person"
        ),
        ERExample(
            example_id="er_person_017",
            mention_1="Patricia White",
            mention_2="Patricia Weiss",
            gold_label="different",
            category="person"
        ),
        ERExample(
            example_id="er_person_018",
            mention_1="Kevin Patrick",
            mention_2="Kevin Patric",
            gold_label="different",
            category="person"
        ),
        ERExample(
            example_id="er_person_019",
            mention_1="Susan Miller",
            mention_2="Suzanne Miller",
            gold_label="uncertain",
            category="person"
        ),
        ERExample(
            example_id="er_person_020",
            mention_1="Christopher Davis",
            mention_2="Christina Davis",
            gold_label="different",
            category="person"
        ),
        ERExample(
            example_id="er_person_021",
            mention_1="Nancy Scott",
            mention_2="N. Scott",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_022",
            mention_1="Edward Martin",
            mention_2="Ed Martin",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_023",
            mention_1="Thomas Richard Robinson",
            mention_2="T. R. Robinson",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_024",
            mention_1="Jennifer Marie Green",
            mention_2="J. M. Green",
            gold_label="same",
            category="person"
        ),
        ERExample(
            example_id="er_person_025",
            mention_1="William Henry Taylor",
            mention_2="W. H. Taylor",
            gold_label="same",
            category="person"
        ),
    ]
    examples.extend(person_examples)

    # ========================================================================
    # Category 2: Organizations (25 examples)
    # ========================================================================

    org_examples = [
        ERExample(
            example_id="er_org_001",
            mention_1="Massachusetts Institute of Technology",
            mention_2="MIT",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_002",
            mention_1="University of California, Los Angeles",
            mention_2="UCLA",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_003",
            mention_1="National Institutes of Health",
            mention_2="NIH",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_004",
            mention_1="World Health Organization",
            mention_2="WHO",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_005",
            mention_1="Johns Hopkins University",
            mention_2="Johns Hopkins",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_006",
            mention_1="California Institute of Technology",
            mention_2="Caltech",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_007",
            mention_1="University of Cambridge",
            mention_2="Cambridge",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_008",
            mention_1="University of Oxford",
            mention_2="Oxford",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_009",
            mention_1="Stanford University",
            mention_2="Stanford",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_010",
            mention_1="Harvard University",
            mention_2="Harvard",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_011",
            mention_1="Yale University",
            mention_2="Yale",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_012",
            mention_1="Princeton University",
            mention_2="Princeton",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_013",
            mention_1="University of Pennsylvania",
            mention_2="U Penn",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_014",
            mention_1="Duke University",
            mention_2="Duke",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_015",
            mention_1="Columbia University",
            mention_2="Columbia",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_016",
            mention_1="University of Chicago",
            mention_2="University of Chicago Medical Center",
            gold_label="uncertain",
            category="org"
        ),
        ERExample(
            example_id="er_org_017",
            mention_1="MIT Media Lab",
            mention_2="MIT",
            gold_label="uncertain",
            category="org"
        ),
        ERExample(
            example_id="er_org_018",
            mention_1="Harvard Medical School",
            mention_2="Harvard",
            gold_label="uncertain",
            category="org"
        ),
        ERExample(
            example_id="er_org_019",
            mention_1="University of California",
            mention_2="UC System",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_020",
            mention_1="UCSF",
            mention_2="University of California, San Francisco",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_021",
            mention_1="Broad Institute",
            mention_2="Broad Institute of MIT and Harvard",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_022",
            mention_1="Max Planck Institute",
            mention_2="Max Planck Society",
            gold_label="different",
            category="org"
        ),
        ERExample(
            example_id="er_org_023",
            mention_1="Bell Labs",
            mention_2="Bell Laboratories",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_024",
            mention_1="CERN",
            mention_2="European Organization for Nuclear Research",
            gold_label="same",
            category="org"
        ),
        ERExample(
            example_id="er_org_025",
            mention_1="NASA",
            mention_2="National Aeronautics and Space Administration",
            gold_label="same",
            category="org"
        ),
    ]
    examples.extend(org_examples)

    # ========================================================================
    # Category 3: Proteins (25 examples)
    # ========================================================================

    protein_examples = [
        ERExample(
            example_id="er_protein_001",
            mention_1="Interferon gamma",
            mention_2="IFN-γ",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_002",
            mention_1="Tumor necrosis factor alpha",
            mention_2="TNF-α",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_003",
            mention_1="Epidermal growth factor",
            mention_2="EGF",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_004",
            mention_1="Transforming growth factor beta",
            mention_2="TGF-β",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_005",
            mention_1="Vascular endothelial growth factor",
            mention_2="VEGF",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_006",
            mention_1="Fibroblast growth factor",
            mention_2="FGF",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_007",
            mention_1="Nerve growth factor",
            mention_2="NGF",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_008",
            mention_1="Interleukin 6",
            mention_2="IL-6",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_009",
            mention_1="Platelet-derived growth factor",
            mention_2="PDGF",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_010",
            mention_1="Hepatocyte growth factor",
            mention_2="HGF",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_011",
            mention_1="p53 protein",
            mention_2="tumor protein p53",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_012",
            mention_1="EGFR",
            mention_2="Epidermal growth factor receptor",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_013",
            mention_1="HER2",
            mention_2="Human epidermal growth factor receptor 2",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_014",
            mention_1="PD-1",
            mention_2="Programmed cell death protein 1",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_015",
            mention_1="PD-L1",
            mention_2="Programmed death ligand 1",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_016",
            mention_1="INF-γ",
            mention_2="IFN-gamma",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_017",
            mention_1="TNFalpha",
            mention_2="TNF-alpha",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_018",
            mention_1="Interleukin-10",
            mention_2="IL10",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_019",
            mention_1="MCP-1",
            mention_2="Monocyte chemoattractant protein-1",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_020",
            mention_1="Interleukin-2",
            mention_2="IL-12",
            gold_label="different",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_021",
            mention_1="TNF receptor 1",
            mention_2="TNF-R1",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_022",
            mention_1="β-actin",
            mention_2="beta actin",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_023",
            mention_1="GAPDH",
            mention_2="Glyceraldehyde-3-phosphate dehydrogenase",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_024",
            mention_1="Caspase-3",
            mention_2="Caspase 3",
            gold_label="same",
            category="protein"
        ),
        ERExample(
            example_id="er_protein_025",
            mention_1="Caspase-9",
            mention_2="Caspase-3",
            gold_label="different",
            category="protein"
        ),
    ]
    examples.extend(protein_examples)

    # ========================================================================
    # Category 4: Chemicals (25 examples)
    # ========================================================================

    chemical_examples = [
        ERExample(
            example_id="er_chem_001",
            mention_1="Aspirin",
            mention_2="Acetylsalicylic acid",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_002",
            mention_1="Ibuprofen",
            mention_2="2-(4-isobutylphenyl)propanoic acid",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_003",
            mention_1="Paracetamol",
            mention_2="Acetaminophen",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_004",
            mention_1="Metformin",
            mention_2="N,N-dimethylbiguanide",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_005",
            mention_1="Lisinopril",
            mention_2="ACE inhibitor",
            gold_label="uncertain",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_006",
            mention_1="Simvastatin",
            mention_2="Statin",
            gold_label="uncertain",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_007",
            mention_1="Vitamin C",
            mention_2="Ascorbic acid",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_008",
            mention_1="Vitamin E",
            mention_2="Tocopherol",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_009",
            mention_1="Cortisol",
            mention_2="Hydrocortisone",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_010",
            mention_1="Glucose",
            mention_2="Dextrose",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_011",
            mention_1="Aspirin",
            mention_2="Ibuprofen",
            gold_label="different",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_012",
            mention_1="Vitamin D",
            mention_2="Cholecalciferol",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_013",
            mention_1="Insulin",
            mention_2="Insulin protein",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_014",
            mention_1="Dopamine",
            mention_2="3,4-dihydroxyphenylalanine",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_015",
            mention_1="Serotonin",
            mention_2="5-hydroxytryptamine",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_016",
            mention_1="Adrenaline",
            mention_2="Epinephrine",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_017",
            mention_1="Penicillin",
            mention_2="Antibiotic",
            gold_label="uncertain",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_018",
            mention_1="Morphine",
            mention_2="7,8-Didehydro-4,5-epoxy-17-methoxymorphinan-3,6-diol",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_019",
            mention_1="Caffeine",
            mention_2="Trimethylxanthine",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_020",
            mention_1="Nicotine",
            mention_2="3-(1-methylpyrrolidin-2-yl)pyridine",
            gold_label="same",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_021",
            mention_1="Ethanol",
            mention_2="Alcohol",
            gold_label="uncertain",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_022",
            mention_1="Salicylic acid",
            mention_2="Acetylsalicylic acid",
            gold_label="different",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_023",
            mention_1="Cholesterol",
            mention_2="Lipid",
            gold_label="uncertain",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_024",
            mention_1="Glucose",
            mention_2="Fructose",
            gold_label="different",
            category="compound"
        ),
        ERExample(
            example_id="er_chem_025",
            mention_1="Sodium chloride",
            mention_2="Salt",
            gold_label="same",
            category="compound"
        ),
    ]
    examples.extend(chemical_examples)

    return examples


if __name__ == "__main__":
    # Load and display examples
    examples = load_entity_resolution_100()

    print(f"Loaded {len(examples)} entity-resolution examples\n")

    # Count by label and category
    label_counts = {}
    category_counts = {}
    for ex in examples:
        label = ex.gold_label
        label_counts[label] = label_counts.get(label, 0) + 1

        category = ex.category
        if category not in category_counts:
            category_counts[category] = {"same": 0, "different": 0, "uncertain": 0}
        category_counts[category][label] += 1

    print("Label distribution (overall):")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")

    print("\nLabel distribution (by category):")
    for category in sorted(category_counts.keys()):
        counts = category_counts[category]
        print(f"  {category}:")
        for label, count in sorted(counts.items()):
            print(f"    {label}: {count}")

    print(f"\nTotal: {len(examples)} examples")

    # Display first few
    print("\nFirst 5 examples:")
    for i, ex in enumerate(examples[:5], 1):
        print(f"\n{i}. {ex.example_id} ({ex.category})")
        print(f"   '{ex.mention_1}' vs. '{ex.mention_2}'")
        print(f"   Gold: {ex.gold_label}")
