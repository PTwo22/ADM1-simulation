"""Exploratory assumptions, NOT fitted RHB550 kinetic measurements."""
REFERENCE_SI = 1.0  # assumed g substrate VS / g inoculum VS
OFFICIAL_S24_SI = 2.0  # tested literature level; less inoculum at fixed substrate
BIOCHAR_MATERIAL = "Rice-husk biochar RHB550 (550 C); uncharacterised batch"
BIOCHAR_MODEL = {
    "benefit_amplitude": 0.5,  # assumed dimensionless kinetic response
    "half_saturation_g_L": 5.0,  # assumed, not measured
    "inhibition_scale_g_L": 30.0,  # assumed, not a measured toxicity threshold
}
SI_LEVELS = (0.33, 0.5, 1.0, 2.0, 4.0)


def extend_scenarios(existing):
    """Copy S3; each official case varies precisely one new input."""
    from copy import deepcopy
    reference = next(s for s in existing if s["id"] == "S3")
    reference.update(biochar_g_L=0.0, si_ratio=REFERENCE_SI)
    additions = []
    for sid, description, dose, ratio in (
        ("S21", "Low biochar addition", 5.0, REFERENCE_SI),
        ("S22", "Moderate biochar addition", 10.0, REFERENCE_SI),
        ("S23", "High biochar addition", 15.0, REFERENCE_SI),
        ("S24", "Reduced inoculum: S:I = 2", 0.0, OFFICIAL_S24_SI),
    ):
        case = deepcopy(reference)
        case.update(id=sid, description=description, biochar_g_L=dose, si_ratio=ratio)
        additions.append(case)
    return additions
