# Blueprints - Content Framework System

This directory contains the semantic blueprints that define Content Engine's content generation frameworks, workflows, and constraints.

## Directory Structure

```
blueprints/
├── frameworks/           # Content structure patterns
│   └── linkedin/        # LinkedIn-specific frameworks
│       ├── STF.yaml     # Storytelling Framework (Problem/Tried/Worked/Lesson)
│       ├── MRS.yaml     # Mistake-Realization-Shift
│       ├── SLA.yaml     # Story-Lesson-Application
│       └── PIF.yaml     # Poll/Interactive Format
├── workflows/           # Multi-step content processes
│   ├── SundayPowerHour.yaml       # Weekly batch creation (10 posts)
│   └── Repurposing1to10.yaml      # One idea → 10 content pieces
├── constraints/         # Brand and platform rules
│   ├── BrandVoice.yaml           # Austin's voice characteristics
│   ├── ContentPillars.yaml       # 4 pillars with distribution
│   └── PlatformRules.yaml        # LinkedIn/Twitter/Blog rules
└── templates/           # Handlebars prompt templates
    └── LinkedInPost.hbs          # LLM prompt for post generation
```

## Blueprint Types

### Frameworks
Content structure patterns that define how to organize ideas into posts. Each framework has:
- **Structure**: Sections/components required
- **Validation rules**: Min/max chars, required elements
- **Compatible pillars**: Which content pillars work with this framework
- **Examples**: Sample posts following the framework

### Workflows
Multi-step processes for content creation. Each workflow has:
- **Steps**: Ordered sequence of operations
- **Inputs/Outputs**: Data flow between steps
- **Prompt templates**: LLM prompts for each step
- **Success metrics**: How to measure workflow effectiveness

### Constraints
Rules that ensure content quality and brand consistency. Constraints include:
- **Brand voice**: Tone, style, forbidden phrases
- **Content pillars**: Topic distribution (what_building, what_learning, sales_tech, problem_solution)
- **Platform rules**: Character limits, formatting, best practices

### Templates
Handlebars templates that combine context + frameworks + constraints into LLM prompts.

## Usage

### Load a Framework
```python
from lib.blueprint_loader import load_framework

stf = load_framework("STF")
print(stf["structure"])  # See framework structure
```

### Load a Constraint
```python
from lib.blueprint_loader import load_constraints

brand_voice = load_constraints("BrandVoice")
print(brand_voice["forbidden_phrases"])
```

### Generate Content with Blueprint
```python
from agents.linkedin.content_generator import generate_post

post = generate_post(
    context=daily_context,
    pillar="what_building",
    framework="STF",
    model="llama3:8b"
)
```

### Validate Generated Content
```python
from agents.linkedin.post_validator import validate_post

report = validate_post(post)
if report.passed:
    print("Post is valid!")
else:
    for violation in report.violations:
        print(f"{violation.severity}: {violation.message}")
```

## File Format

All blueprint files use YAML format with a standard structure:

```yaml
name: BlueprintName
type: framework | workflow | constraint
platform: linkedin | twitter | blog | multi
description: Brief description of what this blueprint does

# Framework-specific fields
structure:
  sections: [...]
validation:
  rules: [...]

# Workflow-specific fields
steps:
  - name: Step Name
    inputs: [...]
    outputs: [...]

# Constraint-specific fields
characteristics: [...]
forbidden_phrases: [...]
validation_rules: [...]
```

## Design Principles

1. **Explicit over implicit**: Every rule is documented in YAML
2. **Composable**: Frameworks + constraints + templates work together
3. **Testable**: Each blueprint can be validated independently
4. **Evolvable**: Easy to add new frameworks or update constraints
5. **AI-friendly**: Structured data for LLM prompts and validation

## Quality Gates

Every generated piece of content must pass:
1. **Framework validation**: Matches structural requirements
2. **Brand voice check**: Aligns with Austin's voice
3. **Platform rules**: Meets character limits and formatting
4. **Pillar distribution**: Maintains content balance across pillars

## Future Expansions

- **Blog frameworks**: Long-form content structures
- **Twitter frameworks**: Thread patterns
- **Video scripts**: YouTube/TikTok templates
- **Carousel designs**: Multi-slide LinkedIn carousels
- **Email sequences**: Newsletter frameworks
