# Examples and Prompts for Semantic Enrichment

**Purpose**: Good/bad examples and AI prompts for graph semantic enrichment
**Version**: 1.0
**Last Updated**: 2025-11-24

---

## 1. MetaAttribute Examples

### Definition Examples

#### ✅ GOOD: Core Cause (M001)

**German**:
```
"Der Core Cause ist der zentrale Beweggrund oder das grundlegende 'Warum'
hinter einer Marke. Er beschreibt die zugrundeliegende Motivation, aus der
heraus die Marke agiert – unabhängig von kurzfristigen Zielen. Der Core
Cause bezeichnet den fundamentalen, übergeordneten Daseinszweck jenseits
von Gewinnerzielung."
```

**Why Good**:
- ✅ 250 chars (within 200-600 range)
- ✅ Explains WHAT (zentrale Beweggrund, grundlegende 'Warum')
- ✅ Explains WHY (übergeordneten Daseinszweck jenseits Gewinnerzielung)
- ✅ References framework (Simon Sinek's 'Warum' implied)
- ✅ Specific to concept

#### ❌ BAD: Generic Template Definition

**German**:
```
"Ein fundamentaler Aspekt von Markenstrategie, der beschreibt die
Kernelemente der Marke."
```

**Why Bad**:
- ❌ 90 chars (too short, below 200 minimum)
- ❌ Template phrase ("Ein fundamentaler Aspekt von...")
- ❌ Vague ("beschreibt die Kernelemente" - what elements?)
- ❌ No WHY explained
- ❌ Circular definition (defines concept using concept itself)

### whatItIs/whatItIsNot Examples

#### ✅ GOOD: Target Customer (M004)

**whatItIsDe**:
```python
[
    "Spezifische Zielgruppe mit definierten demografischen Merkmalen",
    "Personas basierend auf realen Kundendaten und Marktforschung",
    "Primäre Käufergruppe mit höchstem Customer Lifetime Value",
    "Segmente mit gemeinsamen Bedürfnissen und Kaufverhalten",
    "Validierte Nutzerprofile aus qualitativer Forschung"
]
```

**whatItIsNotDe**:
```python
[
    "Nicht 'alle Menschen' oder undifferenzierte Masse",
    "Nicht nur demografische Daten ohne psychografische Insights",
    "Nicht Wunschkunden ohne Marktvalidierung",
    "Nicht statische Zielgruppe ohne Entwicklungspotenzial",
    "Nicht identisch mit aktueller Kundenbasis"
]
```

**Why Good**:
- ✅ 5 items each (within 3-7 range)
- ✅ Specific characteristics (not generic)
- ✅ Clear contrast between Is/IsNot
- ✅ References methodology (personas, CLV, segmentation)
- ✅ No overlap between lists

#### ❌ BAD: Generic Lists

**whatItIsDe**:
```python
[
    "Wichtig für die Marke",
    "Strategisch relevant"
]
```

**whatItIsNotDe**:
```python
[
    "Nicht unwichtig"
]
```

**Why Bad**:
- ❌ Only 2 items (below 3 minimum)
- ❌ Too generic (apply to everything)
- ❌ No specific characteristics
- ❌ Meaningless negation
- ❌ No semantic value

---

## 2. Enumeration Examples

### Differentiated Enumerations

#### ✅ GOOD: Tech Enthusiasts vs Luxury Buyers

**E-00042: Tech Enthusiasts**
```python
{
    "definitionDe": "Frühadoptierer neuer Technologien mit hoher digitaler
                     Kompetenz, die Innovation und Funktionalität über
                     Ästhetik stellen. Typischerweise 25-40 Jahre, überdurch-
                     schnittliches Einkommen, urban lebend.",
    "whatItIsDe": [
        "Early Adopter mit Risikobereitschaft für neue Produkte",
        "Digital Natives mit tiefem Technologieverständnis",
        "Community-aktiv in Tech-Foren und Beta-Tests",
        "Performance-orientiert statt statusgetrieben"
    ],
    "whatItIsNotDe": [
        "Nicht Mainstream-Käufer die auf bewährte Lösungen warten",
        "Nicht primär statusorientierte Luxuskäufer",
        "Nicht preissensitive Schnäppchenjäger",
        "Nicht technologiefeindliche Traditionalisten"
    ]
}
```

**E-00234: Luxury Buyers**
```python
{
    "definitionDe": "Premiumkunden mit Fokus auf Exklusivität, Handwerkskunst
                     und Statussymbolik. Wertschätzen Heritage-Marken,
                     limitierte Editionen und personalisierte Erlebnisse.
                     Kaufentscheidungen emotional statt rational.",
    "whatItIsDe": [
        "Statusbewusste Käufer mit Markenpräferenz",
        "Qualitätsorientiert mit Fokus auf Handwerkskunst",
        "Exklusivität suchend durch limitierte Verfügbarkeit",
        "Erlebnisorientiert statt rein produktfokussiert"
    ],
    "whatItIsNotDe": [
        "Nicht Early Adopter unerprobter Technologien",
        "Nicht primär funktionsorientierte Käufer",
        "Nicht preissensitive Vergleichskäufer",
        "Nicht DIY-orientierte Selbstoptimierer"
    ]
}
```

**Why Good**: Clear differentiation, contrasting characteristics, specific attributes

---

## 3. AI Enrichment Prompts

### MetaAttribute Definition Prompt

```
You are enriching the MetaAttribute "{name}" for a brand strategy graph.

Current properties from SOURCE:
- Name: {nameDe}
- Type: {attributeType}
- Layer: {layer}
- Group: {group}

Generate a definition (200-600 chars) that:
1. Explains WHAT this concept is (first sentence)
2. Explains WHY it matters in branding context (second sentence)
3. Provides specific context or framework reference
4. Is specific to THIS concept, not generic

BANNED phrases to avoid:
- "Ein fundamentaler Aspekt von..."
- "Bezieht sich auf..."
- "Ist relevant für..."
- Any template phrases

Example of good definition:
"Der Core Cause ist der zentrale Beweggrund oder das grundlegende 'Warum'
hinter einer Marke. Er beschreibt die zugrundeliegende Motivation, aus der
heraus die Marke agiert – unabhängig von kurzfristigen Zielen."

Generate definitionDe:
```

### whatItIs Generation Prompt

```
Generate 3-7 specific characteristics for "{name}" that differentiate it
from similar concepts.

Each item should be:
- 15-80 characters
- Specific to this concept
- Reference frameworks or methodologies where applicable
- Not generic statements

Good example for "Core Cause":
[
    "Fundamentaler Daseinszweck jenseits von Gewinnerzielung",
    "Übergeordnetes 'Warum' nach Simon Sinek's Golden Circle",
    "Langfristig stabil (nicht kurzfristig änderbar)",
    "Motiviert alle strategischen Entscheidungen"
]

Generate whatItIsDe list:
```

### whatItIsNot Generation Prompt

```
Generate 3-7 contrasting points for "{name}" that clarify boundaries
and prevent misconceptions.

Each item should:
- Differentiate from similar but different concepts
- Address common misconceptions
- Provide semantic contrast to whatItIs
- Be specific, not generic negations

Good example for "Core Cause":
[
    "Nicht identisch mit Vision oder Mission Statement",
    "Nicht primär auf Gewinnmaximierung ausgerichtet",
    "Nicht oberflächliches Marketing-Versprechen",
    "Nicht kurzfristig änderbar oder anpassbar"
]

Generate whatItIsNotDe list:
```

### brandingRelevance Prompt

```
Explain the strategic value of "{name}" in branding context (200-600 chars).

Include:
- Why this matters for brand strategy
- Concrete use cases or applications
- Impact on business outcomes
- Connection to other brand elements

Example:
"Der Core Cause ist fundamental für authentische Markenführung. Er bildet die
Basis für konsistente Kommunikation, motiviert Mitarbeiter intrinsisch und
schafft emotionale Kundenbindung. Marken mit klar definiertem Core Cause
zeigen höhere Resilienz in Krisen und differenzieren sich nachhaltig."

Generate brandingRelevanceDe:
```

---

## 4. Edge Property Examples

### assignmentReasoning (HAS_ATTRIBUTE)

#### ✅ GOOD Example

```
"M001 (Core Cause) assigned to Foundation layer because it defines the
fundamental 'why' of brand existence, serving as prerequisite for all
strategic decisions. Foundation layer must stabilize before Strategy layer
can be built upon it, ensuring inside-out coherence from core values
outward to expression."
```

**Why Good**:
- ✅ 280 chars (within 200-600 range)
- ✅ Explains WHY this layer (prerequisite, foundation stability)
- ✅ References layer processing order
- ✅ Mentions brand architecture principle

#### ❌ BAD Example

```
"Assigned to Foundation because it's a foundational attribute."
```

**Why Bad**:
- ❌ 60 chars (below 200 minimum)
- ❌ Circular reasoning
- ❌ No semantic explanation

### groupingReasoning (BELONGS_TO_GROUP)

#### ✅ GOOD Example

```
"M001 grouped in 'brand_core' because it articulates the central purpose
alongside mission and vision, forming a conceptual cluster of foundational
identity elements that define why the organization exists. These attributes
collectively represent the deepest layer of brand DNA and are prerequisite
to strategic positioning decisions."
```

**Why Good**:
- ✅ 320 chars (within range)
- ✅ Explains thematic coherence
- ✅ Identifies semantic relationships
- ✅ Explains strategic value

---

## 5. Validation Feedback Examples

### Template Phrase Detection

**Error Message**:
```json
{
    "status": "error",
    "tier2_passed": false,
    "violations": [
        "Template phrase 'Ein fundamentaler Aspekt von' detected in definitionDe"
    ],
    "suggestions": [
        "Explain WHAT this concept specifically is",
        "Explain WHY it matters in branding",
        "Avoid generic descriptions that could apply to any concept"
    ],
    "example": "Der [Concept] ist [specific explanation of what it is]..."
}
```

### Length Violation

**Error Message**:
```json
{
    "status": "error",
    "tier1_passed": false,
    "violations": [
        "definitionDe too short (120 chars). Must be 200-600 chars."
    ],
    "suggestions": [
        "Add explanation of WHAT this concept is",
        "Add explanation of WHY it matters",
        "Include context or framework reference"
    ],
    "current_length": 120,
    "required_range": [200, 600]
}
```

### Insufficient Contrast

**Error Message**:
```json
{
    "status": "error",
    "tier2_passed": false,
    "violations": [
        "whatItIsDe and whatItIsNotDe have overlapping items"
    ],
    "overlapping_items": [
        "Strategic importance"
    ],
    "suggestions": [
        "Ensure whatItIs and whatItIsNot are mutually exclusive",
        "whatItIsNot should clarify boundaries, not repeat whatItIs"
    ]
}
```

---

## 6. Brand Example Templates

### EXEMPLIFIED_BY Relationship

#### ✅ GOOD: Patagonia for Environmental Protection

```cypher
(:Enumeration {nameDe: "Umweltschutz"})-[:EXEMPLIFIED_BY {
    reasoning: "Patagonia exemplifies 'Environmental Protection' through
               concrete, measurable actions: 1% for the Planet donations
               ($140M since 1985), Worn Wear repair program reducing consumption,
               political environmental advocacy including lawsuits against
               government, transparent supply chain reporting. Environmental
               mission embedded in organizational DNA from founding, not
               marketing overlay. 2022: Chouinard transferred ownership to
               environmental trust, demonstrating authentic commitment.",
    context: "Founded by Yvon Chouinard 1973 with mission 'We're in business
             to save our home planet'. Certified B-Corp since 2012. Annual
             revenue ~$1B, proving environmental focus compatible with
             business success.",
    source: "https://www.patagonia.com/our-footprint/",
    retrievalDate: date("2025-11-24")
}]->(:BrandExample {
    brandName: "Patagonia",
    industry: "Outdoor Apparel",
    foundedYear: 1973,
    url: "https://www.patagonia.com"
})
```

**Why Good**:
- ✅ Concrete actions with evidence
- ✅ Multiple dimensions of exemplification
- ✅ Historical continuity shown
- ✅ Verifiable source provided
- ✅ Context explains brand background

#### ❌ BAD: Vague Example

```
reasoning: "Patagonia is environmentally friendly"
context: "They care about nature"
source: "Common knowledge"
```

**Why Bad**:
- ❌ No specific actions
- ❌ Too vague
- ❌ Not verifiable
- ❌ No evidence provided

---

## 7. Regeneration Prompts

### When Template Phrase Detected

```
The definition contains the banned phrase "{detected_phrase}".

Original: "{original_definition}"

Regenerate WITHOUT using:
- Ein fundamentaler Aspekt von...
- Bezieht sich auf...
- Ist relevant für...
- Umfasst alle Aspekte von...

Instead:
1. Start with WHAT this concept IS
2. Explain WHY it matters
3. Be specific to THIS concept

Good pattern:
"Der [Concept] ist [specific definition]... Er/Sie [why it matters]..."

Regenerate definitionDe:
```

### When Too Generic

```
The whatItIs items are too generic:
{current_items}

These could apply to many concepts. Generate SPECIFIC characteristics for "{name}".

Ask yourself:
- What makes THIS different from similar concepts?
- What frameworks or methodologies apply?
- What measurable aspects exist?
- What unique behaviors or patterns?

Generate specific whatItIsDe list:
```

### When Lacking Contrast

```
The whatItIsNot list doesn't provide sufficient contrast:
{current_items}

Generate items that:
- Differentiate from SIMILAR but different concepts
- Address common MISCONCEPTIONS
- Clarify BOUNDARIES
- Prevent CONFUSION with related ideas

For "{name}", what is it commonly confused with?
What boundaries need clarification?

Generate contrasting whatItIsNotDe list:
```

---

## 8. Quality Checklist

Before committing any enrichment, verify:

### Definition Quality
- [ ] Length: 200-600 characters
- [ ] Explains WHAT (first part)
- [ ] Explains WHY (second part)
- [ ] No template phrases
- [ ] Specific to concept

### whatItIs Quality
- [ ] Count: 3-7 items
- [ ] Length: 15-80 chars each
- [ ] Specific characteristics
- [ ] Framework references where applicable
- [ ] No generic statements

### whatItIsNot Quality
- [ ] Count: 3-7 items
- [ ] Provides semantic contrast
- [ ] Differentiates from similar concepts
- [ ] No overlap with whatItIs
- [ ] Addresses misconceptions

### brandingRelevance Quality
- [ ] Length: 200-600 characters
- [ ] Strategic value explained
- [ ] Use cases provided
- [ ] Impact described
- [ ] Connection to brand strategy

### Edge Property Quality
- [ ] assignmentReasoning: 200-600 chars
- [ ] groupingReasoning: 200-600 chars
- [ ] Explains WHY, not just states fact
- [ ] References principles or frameworks
- [ ] No circular reasoning

---

## Key Principles

1. **Specificity over generality** - Every property must be specific to the concept
2. **Evidence over assertion** - Provide examples, frameworks, methodologies
3. **Contrast over repetition** - whatItIsNot must clarify boundaries
4. **Reasoning over description** - Explain WHY, not just WHAT
5. **Regeneration over settlement** - Keep improving until quality achieved

---

**Remember**: These examples guide semantic enrichment. Quality matters more than speed. Regenerate as many times as needed to achieve specificity and avoid template phrases.