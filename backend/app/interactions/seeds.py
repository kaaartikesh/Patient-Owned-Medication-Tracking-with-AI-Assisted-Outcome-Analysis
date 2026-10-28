from sqlalchemy.orm import Session
from app.models.interaction import DrugInteraction

DEFAULT_INTERACTIONS = [
    {
        "drug_a": "warfarin",
        "drug_b": "aspirin",
        "severity": "HIGH",
        "description": "Concurrent anticoagulant and antiplatelet therapy substantially increases the risk of major hemorrhage.",
    },
    {
        "drug_a": "warfarin",
        "drug_b": "ibuprofen",
        "severity": "HIGH",
        "description": "NSAIDs damage GI mucosa and impair platelet aggregation, markedly elevating bleeding risk with warfarin.",
    },
    {
        "drug_a": "sildenafil",
        "drug_b": "nitroglycerin",
        "severity": "CRITICAL",
        "description": "Potentiation of nitric oxide-mediated vasodilation leads to life-threatening, refractory hypotension.",
    },
    {
        "drug_a": "lisinopril",
        "drug_b": "potassium",
        "severity": "HIGH",
        "description": "ACE inhibitors reduce aldosterone secretion, precipitating dangerous cardiac arrhythmias due to hyperkalemia.",
    },
    {
        "drug_a": "simvastatin",
        "drug_b": "amiodarone",
        "severity": "HIGH",
        "description": "CYP3A4 inhibition increases simvastatin plasma concentrations, raising the risk of severe rhabdomyolysis.",
    },
    {
        "drug_a": "fluoxetine",
        "drug_b": "tramadol",
        "severity": "HIGH",
        "description": "Additive serotonergic activity increases the danger of central serotonin syndrome and lowers seizure threshold.",
    },
    {
        "drug_a": "clopidogrel",
        "drug_b": "omeprazole",
        "severity": "MODERATE",
        "description": "Omeprazole inhibits CYP2C19 bioactivation of clopidogrel, diminishing its cardioprotective antiplatelet effect.",
    },
    {
        "drug_a": "methotrexate",
        "drug_b": "ibuprofen",
        "severity": "HIGH",
        "description": "NSAIDs compete with methotrexate renal tubular secretion, causing dangerous myelosuppression and toxicity.",
    },
    {
        "drug_a": "ciprofloxacin",
        "drug_b": "theophylline",
        "severity": "HIGH",
        "description": "Ciprofloxacin inhibits hepatic CYP1A2, leading to elevated theophylline levels, nausea, and seizures.",
    },
    {
        "drug_a": "paroxetine",
        "drug_b": "selegiline",
        "severity": "CRITICAL",
        "description": "Concurrent SSRI and MAO inhibitor administration triggers catastrophic serotonin crisis and hyperthermia.",
    },
    {
        "drug_a": "metformin",
        "drug_b": "contrast",
        "severity": "HIGH",
        "description": "Iodinated radiocontrast can impair renal function, leading to toxic metformin accumulation and fatal lactic acidosis.",
    },
    {
        "drug_a": "levothyroxine",
        "drug_b": "calcium",
        "severity": "MODERATE",
        "description": "Calcium carbonate binds to levothyroxine in the gastrointestinal tract, significantly decreasing absorption.",
    },
]


def seed_drug_interactions(db: Session) -> None:
    """Populates the local drug_interactions lookup table if empty."""
    existing_count = db.query(DrugInteraction).count()
    if existing_count == 0:
        for item in DEFAULT_INTERACTIONS:
            interaction = DrugInteraction(
                drug_a=item["drug_a"].lower().strip(),
                drug_b=item["drug_b"].lower().strip(),
                severity=item["severity"],
                description=item["description"],
            )
            db.add(interaction)
        db.commit()
