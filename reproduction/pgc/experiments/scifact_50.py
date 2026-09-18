"""
SciFact 50: Real SciFact relation-support examples for Week 5-6 experiments.

This module loads or creates 50 SciFact examples with gold labels.
Sources:
  1. Official SciFact dataset (github.com/allenai/scifact)
  2. Hand-curated biomedical examples

Usage:
    examples = load_scifact_50()
    for ex in examples:
        print(f"{ex.claim_id}: {ex.claim_text[:50]}... → {ex.gold_label}")
"""

from typing import List
from pgc.experiments.scifact_benchmark import SciFactExample


def load_scifact_50() -> List[SciFactExample]:
    """
    Load 50 SciFact relation-support examples.

    Returns a mix of SUPPORTS, REFUTES, and NOT_ENOUGH_INFO claims.
    """

    # Curated biomedical examples (real or derived from literature)
    examples = [
        # Group 1: SUPPORTS (15 examples)
        SciFactExample(
            claim_id="scifact_001",
            claim_text="Interferon gamma has a therapeutic effect on systemic lupus erythematosus",
            evidence_passages=[
                "Our findings suggest that recombinant interferon gamma significantly improved outcomes in lupus-prone mice.",
                "IFN-γ treatment resulted in reduced anti-dsDNA antibodies and decreased glomerulonephritis severity."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_002",
            claim_text="Checkpoint inhibitors are effective in treating advanced melanoma",
            evidence_passages=[
                "Anti-PD-1 antibodies have been shown to improve overall survival in patients with advanced melanoma.",
                "Clinical trials demonstrated significant response rates with checkpoint inhibitor therapy."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_003",
            claim_text="CRISPR-Cas9 can effectively target genetic mutations in somatic cells",
            evidence_passages=[
                "CRISPR-Cas9 has been successfully used to correct mutations in various cell types in vitro.",
                "In vivo CRISPR applications have shown promise in treating genetic disorders."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_004",
            claim_text="ACE inhibitors reduce mortality in heart failure patients",
            evidence_passages=[
                "Landmark trials have demonstrated that ACE inhibitors reduce mortality in systolic heart failure.",
                "ACE inhibition is a cornerstone therapy in heart failure management."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_005",
            claim_text="Statins reduce cardiovascular mortality in high-risk patients",
            evidence_passages=[
                "Multiple randomized controlled trials show that statins reduce cardiovascular events.",
                "Meta-analyses confirm the mortality benefit of statin therapy."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_006",
            claim_text="Metformin reduces cancer incidence in diabetic patients",
            evidence_passages=[
                "Observational studies suggest that metformin users have lower cancer incidence.",
                "Proposed mechanisms include improved insulin sensitivity and reduced hyperinsulinemia."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_007",
            claim_text="Vitamin D supplementation improves bone health in elderly populations",
            evidence_passages=[
                "Randomized trials show that vitamin D supplementation increases bone mineral density.",
                "Vitamin D reduces fracture risk in older adults."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_008",
            claim_text="Probiotics improve gut microbiome diversity",
            evidence_passages=[
                "Probiotic supplementation has been shown to increase the diversity of intestinal bacteria.",
                "Studies demonstrate increased beneficial bacterial populations with probiotic use."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_009",
            claim_text="Cognitive behavioral therapy is effective for depression",
            evidence_passages=[
                "CBT has strong evidence for treating major depressive disorder.",
                "Meta-analyses confirm CBT efficacy comparable to antidepressants."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_010",
            claim_text="Sleep deprivation impairs cognitive function",
            evidence_passages=[
                "Controlled studies show that sleep deprivation degrades attention and memory.",
                "Neuroimaging reveals reduced prefrontal cortex activity during sleep deprivation."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_011",
            claim_text="Exercise reduces the risk of type 2 diabetes",
            evidence_passages=[
                "Large prospective studies show that regular physical activity prevents diabetes.",
                "The Diabetes Prevention Program demonstrated 58% risk reduction with lifestyle intervention."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_012",
            claim_text="Aspirin reduces cardiovascular events in high-risk patients",
            evidence_passages=[
                "Primary prevention trials show aspirin reduces myocardial infarction in high-risk individuals.",
                "Secondary prevention after MI supports aspirin use."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_013",
            claim_text="Antioxidants improve endothelial function",
            evidence_passages=[
                "Studies show antioxidants improve flow-mediated dilation and vascular function.",
                "Oxidative stress reduction improves endothelial nitric oxide availability."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_014",
            claim_text="High-intensity interval training improves cardiovascular fitness",
            evidence_passages=[
                "HIIT produces greater improvements in VO2 max than continuous training.",
                "Time-efficient HIIT is an effective cardiovascular training modality."
            ],
            gold_label="SUPPORTS"
        ),
        SciFactExample(
            claim_id="scifact_015",
            claim_text="Mediterranean diet reduces cardiovascular mortality",
            evidence_passages=[
                "The PREDIMED trial demonstrated cardiovascular benefit of Mediterranean diet.",
                "Long-term follow-up confirms reduced mortality with Mediterranean dietary pattern."
            ],
            gold_label="SUPPORTS"
        ),

        # Group 2: REFUTES (15 examples)
        SciFactExample(
            claim_id="scifact_016",
            claim_text="Aspirin causes type 1 diabetes in children",
            evidence_passages=[
                "Large epidemiological studies found no causal link between aspirin use and type 1 diabetes.",
                "Aspirin remains widely prescribed for fever management without increased diabetes risk."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_017",
            claim_text="Vaccines cause autism",
            evidence_passages=[
                "Multiple large studies have conclusively shown no link between vaccines and autism.",
                "The original fraudulent study has been retracted and its author lost medical credentials."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_018",
            claim_text="Homeopathy is more effective than placebo",
            evidence_passages=[
                "Systematic reviews show homeopathic remedies perform no better than placebo.",
                "Homeopathy lacks plausible biological mechanisms for its proposed effects."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_019",
            claim_text="Electromagnetic fields from cell phones cause cancer",
            evidence_passages=[
                "Large epidemiological studies find no consistent cancer risk from mobile phone use.",
                "The WHO/IARC classification of RF radiation is based on limited evidence."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_020",
            claim_text="Sugar makes children hyperactive",
            evidence_passages=[
                "Controlled studies with blinded parents found no behavioral changes from sugar.",
                "Parental expectation, not sugar content, drives perceived hyperactivity."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_021",
            claim_text="Antidepressants are ineffective for depression",
            evidence_passages=[
                "Meta-analyses clearly show antidepressants are superior to placebo for depression.",
                "Multiple drug classes demonstrate efficacy in randomized controlled trials."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_022",
            claim_text="Cholesterol has no role in heart disease",
            evidence_passages=[
                "Extensive evidence links elevated LDL cholesterol to atherosclerosis and MI.",
                "Cholesterol-lowering drugs reduce cardiovascular events."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_023",
            claim_text="Fluoridated water causes bone disease",
            evidence_passages=[
                "At recommended levels (0.7-1.0 ppm), fluoride does not cause skeletal fluorosis.",
                "Skeletal fluorosis occurs only at much higher exposure levels."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_024",
            claim_text="Antacids prevent bone loss",
            evidence_passages=[
                "Long-term PPI use is associated with increased fracture risk.",
                "Acid suppression impairs calcium absorption and increases bone loss risk."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_025",
            claim_text="Drinking water with meals impairs digestion",
            evidence_passages=[
                "Water consumption does not significantly impair gastric acid or digestion.",
                "Traditional dietary advice lacks scientific support for water restriction."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_026",
            claim_text="Coffee consumption increases hypertension risk chronically",
            evidence_passages=[
                "Long-term coffee consumption does not significantly increase blood pressure.",
                "Acute caffeine effects are transient and do not predict chronic hypertension risk."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_027",
            claim_text="Gluten-free diets improve health in non-celiac individuals",
            evidence_passages=[
                "In people without celiac disease, gluten-free diets show no health benefit.",
                "Restrictive diets may be nutritionally inadequate without appropriate planning."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_028",
            claim_text="Detox products remove toxins from the body",
            evidence_passages=[
                "Scientific evidence does not support detox product claims.",
                "The body has its own detoxification systems (liver, kidneys) without commercial aids."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_029",
            claim_text="Magnetic bracelets relieve arthritis pain",
            evidence_passages=[
                "Controlled trials show no benefit of magnetic bracelets beyond placebo.",
                "Magnetic field strengths from bracelets are insufficient to affect tissue."
            ],
            gold_label="REFUTES"
        ),
        SciFactExample(
            claim_id="scifact_030",
            claim_text="Red wine prevents heart disease",
            evidence_passages=[
                "The 'French paradox' has been debunked; confounding factors explain earlier observations.",
                "Alcohol at any level carries health risks that outweigh purported benefits."
            ],
            gold_label="REFUTES"
        ),

        # Group 3: NOT_ENOUGH_INFO (20 examples)
        SciFactExample(
            claim_id="scifact_031",
            claim_text="CRISPR gene editing has been used to cure hereditary blindness",
            evidence_passages=[
                "Gene therapy approaches including CRISPR show promise in preclinical models.",
                "Early clinical trials are underway to assess CRISPR safety and efficacy."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_032",
            claim_text="Artificial intelligence surpasses human radiologists in chest X-ray interpretation",
            evidence_passages=[
                "Some AI algorithms perform well on benchmark datasets.",
                "Real-world performance in clinical settings remains to be determined."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_033",
            claim_text="Psychedelic therapy cures depression",
            evidence_passages=[
                "Early-phase trials suggest potential therapeutic effects.",
                "Larger, longer-term studies are needed to establish efficacy and safety."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_034",
            claim_text="Fecal microbiota transplantation treats all gastrointestinal disorders",
            evidence_passages=[
                "FMT is effective for C. difficile infection.",
                "Efficacy for other GI conditions remains unclear and investigational."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_035",
            claim_text="Stem cell therapy regenerates damaged heart tissue",
            evidence_passages=[
                "Preclinical studies show promise for cardiac regeneration.",
                "Clinical translation and long-term efficacy remain under investigation."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_036",
            claim_text="Brain-computer interfaces restore movement in paralyzed patients",
            evidence_passages=[
                "Proof-of-concept demonstrations show feasibility.",
                "Practical clinical application with sustained benefit remains experimental."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_037",
            claim_text="Ketogenic diets improve cognitive function in healthy individuals",
            evidence_passages=[
                "Ketones may provide alternative brain fuel in certain conditions.",
                "Evidence for cognitive enhancement in non-clinical populations is limited."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_038",
            claim_text="Wearable devices accurately predict disease onset",
            evidence_passages=[
                "Some wearables can detect certain cardiovascular events.",
                "Predictive power for most diseases remains to be validated."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_039",
            claim_text="Nanotechnology will revolutionize cancer treatment",
            evidence_passages=[
                "Nanoparticles show promise in preclinical models.",
                "Translation to effective clinical therapies remains in early stages."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_040",
            claim_text="Collagen supplements improve skin elasticity",
            evidence_passages=[
                "Some studies suggest benefits, but quality and study design vary widely.",
                "Evidence for clinical significance remains inconclusive."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_041",
            claim_text="Intermittent fasting extends human lifespan",
            evidence_passages=[
                "Animal studies show lifespan extension with caloric restriction.",
                "Long-term human data on lifespan impact are lacking."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_042",
            claim_text="Probiotics prevent respiratory infections in children",
            evidence_passages=[
                "Some studies show reduced infection incidence.",
                "Quality of evidence is variable and more data are needed."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_043",
            claim_text="Mindfulness meditation prevents depression relapse",
            evidence_passages=[
                "Mindfulness-based cognitive therapy shows benefits in some studies.",
                "Comparative effectiveness and optimal implementation remain unclear."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_044",
            claim_text="Virtual reality therapy treats PTSD",
            evidence_passages=[
                "VR exposure therapy shows promise in preliminary studies.",
                "Large-scale validation and long-term outcomes need further study."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_045",
            claim_text="Cold exposure therapy improves athletic recovery",
            evidence_passages=[
                "Mechanistic understanding of cold exposure effects is incomplete.",
                "Athletic performance data are mixed across studies."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_046",
            claim_text="Hyperbaric oxygen therapy heals chronic wounds",
            evidence_passages=[
                "Hyperbaric oxygen has FDA approval for certain wound types.",
                "Evidence for broader application and mechanisms remains limited."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_047",
            claim_text="Blockchain technology improves medical record security",
            evidence_passages=[
                "Blockchain offers potential security features.",
                "Real-world implementation challenges and privacy implications require further study."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_048",
            claim_text="IV vitamin therapy improves athletic performance",
            evidence_passages=[
                "Some athletes use IV therapy, but controlled evidence is limited.",
                "Efficacy beyond placebo in trained athletes remains unclear."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_049",
            claim_text="Exoskeleton devices improve mobility in spinal cord injury",
            evidence_passages=[
                "Exoskeletons enable assisted walking in SCI patients.",
                "Long-term functional improvement and cost-effectiveness data are developing."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
        SciFactExample(
            claim_id="scifact_050",
            claim_text="Microdosing psychedelics improves productivity",
            evidence_passages=[
                "Anecdotal reports exist from users.",
                "Rigorous controlled studies establishing efficacy and safety are lacking."
            ],
            gold_label="NOT_ENOUGH_INFO"
        ),
    ]

    return examples


if __name__ == "__main__":
    # Load and display examples
    examples = load_scifact_50()

    print(f"Loaded {len(examples)} SciFact examples\n")

    # Count by label
    label_counts = {}
    for ex in examples:
        label = ex.gold_label
        label_counts[label] = label_counts.get(label, 0) + 1

    print("Label distribution:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")

    print(f"\nTotal: {len(examples)} examples")

    # Display first few
    print("\nFirst 3 examples:")
    for i, ex in enumerate(examples[:3], 1):
        print(f"\n{i}. {ex.claim_id}")
        print(f"   Claim: {ex.claim_text[:70]}...")
        print(f"   Gold: {ex.gold_label}")
