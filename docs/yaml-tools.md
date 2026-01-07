# YAML Mock Tools

Create mock tools for AI scenarios without writing Python code. Define tools entirely in YAML with support for parameters, conditional returns, state management, and side effects.

## Quick Start

### 1. Create a Tool Library

```bash
sandboxy new tool hospital
```

This creates `tools/mock_hospital.yml`:

```yaml
name: mock_hospital
description: Hospital scenario tools

tools:
  check_vitals:
    description: "Check patient vital signs"
    params:
      patient_id:
        type: string
        required: true
    returns: "Patient {patient_id}: BP 120/80, HR 72, Temp 98.6F"
```

### 2. Create a Scenario

```bash
sandboxy new scenario emergency-room
```

Edit `scenarios/emergency_room.yml`:

```yaml
id: emergency-room
name: "Emergency Room"

tools_from:
  - mock_hospital

initial_state:
  patient_status: "critical"

system_prompt: |
  You are an ER doctor. Assess and treat patients.

steps:
  - id: patient_arrives
    action: inject_user
    params:
      content: "Patient arriving with chest pain!"

  - id: response
    action: await_agent
```

### 3. Run It

```bash
sandboxy scenario scenarios/emergency_room.yml -m openai/gpt-4o-mini -p
```

---

## Tool Definition Reference

### Basic Tool

```yaml
tools:
  my_tool:
    description: "What this tool does"
    params:
      param_name:
        type: string
        required: true
        description: "Parameter description"
    returns: "Result with {param_name} interpolated"
```

### Parameter Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text value | `"hello"` |
| `integer` | Whole number | `42` |
| `number` | Decimal number | `3.14` |
| `boolean` | True/false | `true` |
| `array` | List of values | `["a", "b"]` |
| `object` | Key-value pairs | `{"key": "value"}` |

### Parameter Options

```yaml
params:
  name:
    type: string
    required: true              # Must be provided
    description: "User's name"  # Shown to AI

  count:
    type: integer
    required: false
    default: 1                  # Used if not provided

  status:
    type: string
    enum: ["active", "inactive", "pending"]  # Restrict values
```

---

## Return Values

### Static Return

```yaml
returns: "Operation completed successfully."
```

### Parameter Interpolation

```yaml
returns: "Hello, {name}! You ordered {count} items."
```

### State Interpolation

Access scenario state with `{state.key}`:

```yaml
returns: |
  Patient: {patient_id}
  Status: {state.patient_status}
  Diagnosis: {state.current_diagnosis}
  Vitals: {state.vitals}
```

### Conditional Returns

Return different values based on state:

```yaml
returns:
  - when: "state.patient_status == 'critical'"
    value: "ALERT: Patient critical! Immediate intervention required."

  - when: "state.patient_status == 'stable'"
    value: "Patient stable. Continue monitoring."

  - when: "default"
    value: "Patient status unknown. Run diagnostics."
```

Conditions support:
- Equality: `==`, `!=`
- Comparison: `<`, `>`, `<=`, `>=`
- Boolean: `and`, `or`, `not`
- State access: `state.key` or direct key name

---

## Error Handling

### Conditional Errors

Return an error when a condition is met:

```yaml
tools:
  perform_surgery:
    params:
      procedure:
        type: string
        required: true
      confirm:
        type: boolean
        required: true

    error_when: "confirm != true"
    returns_error: "Surgery requires explicit confirmation. Set confirm=true."

    returns: "Surgery '{procedure}' completed successfully."
```

### State-Based Errors

Prevent actions based on state:

```yaml
tools:
  administer_medication:
    params:
      medication:
        type: string
        required: true

    error_when: "state.allergies_checked != true"
    returns_error: "Must check patient allergies before administering medication."

    returns: "Administered {medication}."
```

---

## Side Effects (State Modification)

Tools can modify scenario state using `side_effects`:

```yaml
tools:
  diagnose_patient:
    params:
      patient_id:
        type: string
        required: true
    returns: "Diagnosis complete for {patient_id}."
    side_effects:
      - set: "diagnosis_completed"
        value: true
      - set: "last_examined"
        value: "{patient_id}"
```

### Dynamic State Keys

Use parameters in state keys:

```yaml
side_effects:
  - set: "patient_{patient_id}_examined"
    value: true
  - set: "patient_{patient_id}_status"
    value: "diagnosed"
```

### State Flow Example

```yaml
tools:
  examine_patient:
    params:
      patient_id:
        type: string
        required: true
    returns: "Examination complete."
    side_effects:
      - set: "examined"
        value: true

  prescribe_treatment:
    params:
      treatment:
        type: string
        required: true
    error_when: "examined != true"
    returns_error: "Must examine patient before prescribing treatment."
    returns: "Prescribed {treatment}."
    side_effects:
      - set: "treatment_prescribed"
        value: "{treatment}"

  discharge_patient:
    error_when: "treatment_prescribed == None or treatment_prescribed == ''"
    returns_error: "Cannot discharge without prescribing treatment."
    returns: "Patient discharged with treatment: {state.treatment_prescribed}"
```

**Flow:**
1. AI must call `examine_patient` first
2. Then `prescribe_treatment` becomes available
3. Finally `discharge_patient` can be called

---

## Scenarios

### Structure

```yaml
id: scenario-id
name: "Human Readable Name"
description: |
  Detailed description of the scenario.

# Tool sources
tools_from:
  - mock_hospital    # Load from tools/mock_hospital.yml
  - mock_pharmacy    # Load from tools/mock_pharmacy.yml

# Inline tools (override or add to library tools)
tools:
  custom_tool:
    description: "Scenario-specific tool"
    returns: "Custom result"

# Starting state
initial_state:
  patient_status: "unknown"
  alert_level: 0

# AI instructions
system_prompt: |
  You are a doctor in an emergency room.
  Use available tools to assess and treat patients.

# Conversation flow
steps:
  - id: initial
    action: inject_user
    params:
      content: "Patient has arrived with symptoms."

  - id: ai_response
    action: await_agent

# Scoring
goals:
  - id: diagnosed
    name: "Made Diagnosis"
    points: 10
    detection:
      type: tool_called
      tool: diagnose_patient

  - id: treated
    name: "Provided Treatment"
    points: 20
    detection:
      type: env_state
      key: treatment_prescribed
      value: true
```

### Variables

Pass variables via CLI:

```bash
sandboxy scenario emergency.yml \
  -v patient="John Smith" \
  -v condition="critical" \
  -m openai/gpt-4o
```

Use in scenario:

```yaml
initial_state:
  patient_name: "{patient}"
  patient_status: "{condition}"

system_prompt: |
  Patient {patient} has arrived in {condition} condition.

steps:
  - id: alert
    action: inject_user
    params:
      content: "Please assess patient {patient} immediately."
```

---

## CLI Reference

### List Available Models

```bash
sandboxy list-models              # Show popular models
sandboxy list-models --free       # Show only free models
sandboxy list-models --fetch      # Fetch full list from OpenRouter
sandboxy list-models -s claude    # Search for models
```

### List Tool Libraries

```bash
sandboxy list-tools
```

### Create New Scenario/Tool

```bash
sandboxy new scenario my-scenario
sandboxy new scenario hospital-er -t "Hospital ER" -d "Emergency room scenario"

sandboxy new tool my-tools
sandboxy new tool hospital -t "Hospital Tools"
```

### Run Scenario

```bash
# Basic
sandboxy scenario scenarios/my-scenario.yml -m openai/gpt-4o-mini

# With variables
sandboxy scenario scenarios/my-scenario.yml \
  -m anthropic/claude-3.5-sonnet \
  -v patient="Jane Doe" \
  -v severity="high"

# Pretty output
sandboxy scenario scenarios/my-scenario.yml -m openai/gpt-4o -p

# Save results
sandboxy scenario scenarios/my-scenario.yml -m openai/gpt-4o -o results.json
```

---

## Goal Detection Types

### Tool Called

```yaml
goals:
  - id: used_diagnosis
    name: "Used Diagnostic Tool"
    points: 10
    detection:
      type: tool_called
      tool: diagnose_patient
```

### Any Tool Called

```yaml
goals:
  - id: took_action
    name: "Took Action"
    points: 15
    detection:
      type: any_tool_called
      tools: ["treat_patient", "prescribe_medication", "refer_specialist"]
```

### State Check

```yaml
goals:
  - id: patient_treated
    name: "Patient Treated"
    points: 20
    detection:
      type: env_state
      key: treatment_completed
      value: true
```

### Agent Response Contains

```yaml
goals:
  - id: explained_reasoning
    name: "Explained Reasoning"
    points: 10
    detection:
      type: agent_contains
      patterns: ["because", "therefore", "diagnosis", "recommend"]
```

---

## Complete Example

`tools/mock_clinic.yml`:

```yaml
name: mock_clinic
description: Medical clinic tools

tools:
  check_symptoms:
    description: "Review patient symptoms"
    params:
      patient_id:
        type: string
        required: true
    returns: |
      Patient {patient_id} Symptoms:
      - {state.primary_symptom}
      - {state.secondary_symptom}
      Duration: {state.symptom_duration}
    side_effects:
      - set: "symptoms_reviewed"
        value: true

  run_tests:
    description: "Run diagnostic tests"
    params:
      test_type:
        type: string
        required: true
        enum: ["blood", "xray", "mri", "ct"]
    error_when: "symptoms_reviewed != true"
    returns_error: "Review symptoms before ordering tests."
    returns: |
      {test_type} results for patient:
      {state.test_results}
    side_effects:
      - set: "tests_completed"
        value: true
      - set: "test_type_used"
        value: "{test_type}"

  make_diagnosis:
    description: "Make a diagnosis based on findings"
    params:
      diagnosis:
        type: string
        required: true
      confidence:
        type: string
        enum: ["low", "medium", "high"]
        required: true
    error_when: "tests_completed != true"
    returns_error: "Run diagnostic tests before making diagnosis."
    returns: "Diagnosis recorded: {diagnosis} (confidence: {confidence})"
    side_effects:
      - set: "diagnosis_made"
        value: "{diagnosis}"
      - set: "diagnosis_confidence"
        value: "{confidence}"

  prescribe_treatment:
    description: "Prescribe treatment plan"
    params:
      treatment:
        type: string
        required: true
      followup_days:
        type: integer
        default: 7
    error_when: "diagnosis_made == None"
    returns_error: "Must make diagnosis before prescribing treatment."
    returns: |
      Treatment prescribed: {treatment}
      Follow-up in {followup_days} days.
      Diagnosis: {state.diagnosis_made}
    side_effects:
      - set: "treatment_prescribed"
        value: "{treatment}"
      - set: "case_completed"
        value: true
```

`scenarios/clinic_visit.yml`:

```yaml
id: clinic-visit
name: "Clinic Visit"
description: Patient arrives with symptoms. Diagnose and treat.

tools_from:
  - mock_clinic

initial_state:
  primary_symptom: "{symptom1}"
  secondary_symptom: "{symptom2}"
  symptom_duration: "{duration}"
  test_results: "Elevated white blood cell count. No structural abnormalities."

system_prompt: |
  You are a physician at a medical clinic.
  A patient has arrived with symptoms.

  Follow proper medical protocol:
  1. Review symptoms
  2. Order appropriate tests
  3. Make a diagnosis
  4. Prescribe treatment

steps:
  - id: patient_arrives
    action: inject_user
    params:
      content: |
        Doctor, I've been experiencing {symptom1} and {symptom2}
        for {duration}. Can you help me?

  - id: doctor_response
    action: await_agent

goals:
  - id: reviewed_symptoms
    name: "Reviewed Symptoms"
    points: 10
    detection:
      type: env_state
      key: symptoms_reviewed
      value: true

  - id: ran_tests
    name: "Ran Diagnostic Tests"
    points: 15
    detection:
      type: env_state
      key: tests_completed
      value: true

  - id: made_diagnosis
    name: "Made Diagnosis"
    points: 20
    detection:
      type: tool_called
      tool: make_diagnosis

  - id: prescribed_treatment
    name: "Prescribed Treatment"
    points: 25
    detection:
      type: env_state
      key: case_completed
      value: true

scoring:
  max_score: 70
```

Run:

```bash
sandboxy scenario scenarios/clinic_visit.yml \
  -m openai/gpt-4o-mini \
  -v symptom1="persistent headache" \
  -v symptom2="mild fever" \
  -v duration="3 days" \
  -p
```

---

## Environment Variables

Set in `.env` or export:

```bash
# Required for paid models
export OPENROUTER_API_KEY=sk-or-...

# Optional: Default model
export SANDBOXY_DEFAULT_MODEL=openai/gpt-4o-mini
```

The CLI automatically loads `.env` from:
1. Current directory
2. `~/.sandboxy/.env`
