# CLAUDE.md - PyGEM Glacier Model Best Practices

This document establishes best practices for working with the PyGEM (Python Glacier Evolution Model) for Dixon Glacier analysis using Claude Code and specialized agents.

## 🎯 Core Principles

### Data Integrity - NEVER FABRICATE DATA
- **CRITICAL**: Only use real simulation data that comes from actual PyGEM model runs
- Never generate, estimate, or make up data values to complete assignments
- If data is missing or unavailable, explicitly state this rather than creating placeholder values
- All results must be traceable to actual model outputs or observational datasets

### Verification Over Trust
- **Always examine file contents** - Never trust filenames or paths from previous agents
- Agent-generated scripts and filenames may contain errors - verify everything
- Check file formats, data structure, and content before using in analysis
- Cross-reference file contents with expected PyGEM input/output specifications

### Comprehensive Progress Logging
- Log all actions with timestamps in a consistent format
- Document next steps and reasoning for each decision
- Track workflow stage completion (calibration → simulation → analysis)
- Maintain clear audit trail of all model runs and parameter changes

## 🔍 Tool and Resource Utilization

### Claude Code Tools & MCP Servers
- **Use all available tools** when applicable: Bash, Read, Edit, Grep, Glob, TodoWrite
- **Leverage MCP servers** for documentation search, web browsing, and specialized tasks
- **Deploy specialized agents** (pygem-glacier-modeler) for complex PyGEM-specific workflows
- **Batch tool calls** when possible for efficiency (multiple file reads, parallel searches)
- **Use Task tool** for complex multi-step operations requiring autonomous execution

### Agent Coordination
- Use pygem-glacier-modeler agent for PyGEM-specific model setup, calibration, and troubleshooting
- Use general-purpose agent for broad research and file system operations
- Document agent handoffs and ensure context preservation between agent calls

## 📊 Model Integrity & Validation

### Pre-Run Validation
- Verify model parameters against reference datasets before simulation
- Check that calibration data (surface change DEM) covers appropriate time periods
- Validate coordinate systems and projections for all spatial data
- Ensure climate data temporal coverage matches simulation requirements

### Data Usage Strategy for Dixon Glacier
- **Calibration**: Use surface_change_2022_2023.TIF for mass balance parameter calibration
- **Validation**: Use stake_observations_dixon.csv for independent validation of calibrated model
- Cross-check calibration results with validation data patterns
- Document any discrepancies between calibration and validation datasets

### Results Validation
- Cross-check calibration results with known Dixon Glacier behavior patterns
- Compare mass balance outputs with stake observation constraints
- Verify outputs against peer-reviewed literature when available
- Flag any results that seem physically unrealistic for Arctic glaciers

## 🔧 Data Handling & Quality Control

### Input Data Verification
```bash
# Always verify data file formats match PyGEM expectations
# .csv for observations, .TIF for DEMs, .shp for outlines
file inputs/stake_observations_dixon.csv
file inputs/surface_change_2022_2023.TIF
```

### Data Quality Checks
- Validate date ranges and temporal consistency in observational data
- Check for missing values, outliers, or data gaps
- Ensure measurement units are consistent (m w.e. for mass balance)
- Verify elevation data falls within reasonable ranges for Dixon Glacier

## ⚙️ Configuration Management

### Config File Safety
```bash
# Always backup config.yaml before modifications
cp ~/PyGEM/config.yaml ~/PyGEM/config.yaml.backup.$(date +%Y%m%d_%H%M%S)
```

### Parameter Documentation
- Document all parameter modifications with scientific rationale
- Test configuration changes on small glacier subsets first
- Maintain separate configs for calibration vs simulation runs
- Record the source/justification for each parameter value

## 🐛 Error Handling & Debugging

### Execution Logging
```bash
# Example logging format for PyGEM script execution
echo "$(date): Starting run_calibration for Dixon Glacier" >> pygem_execution.log
run_calibration -option_calibration option 2>&1 | tee -a pygem_execution.log
echo "$(date): Calibration completed with exit code $?" >> pygem_execution.log
```

### Error Analysis
- Capture and analyze complete error messages from PyGEM scripts
- Check system requirements and dependencies before running
- Monitor memory usage for computationally intensive operations
- Document error resolution steps for future reference

## 🔄 Reproducibility & Documentation

### Version Control
- Record exact PyGEM version and commit hash used
- Document all preprocessing steps and data sources
- Save intermediate results at each workflow stage
- Create detailed run logs with command-line arguments used

### Documentation Standards
```markdown
## Run Record Template
**Date**: YYYY-MM-DD HH:MM
**PyGEM Version**: X.X.X
**Stage**: Calibration/Simulation/Analysis
**Command**: `run_calibration -option_calibration DEBMASS_HIST`
**Input Data**: 
  - surface_change_2022_2023.TIF (for calibration)
  - stake_observations_dixon.csv (for validation)
**Output**: 
  - Calibration parameters in Output/calibration/01/
**Notes**: [Detailed observations and next steps]
```

## 🧪 Scientific Best Practices

### PyGEM Workflow Adherence
1. **Pre-processing**: Verify OGGM glacier directories are current
2. **Configuration**: Set appropriate `root` path and `overwrite_gdirs` settings
3. **Frontal Ablation Calibration**: (if applicable for marine-terminating portions)
4. **Mass Balance Calibration**: Use surface change DEM for parameter optimization
5. **Glen A Calibration**: Regional ice viscosity parameter calibration
6. **Simulation**: Run with validated parameters
7. **Validation**: Compare results against stake observation data
8. **Post-processing**: Aggregate and analyze results

### Iterative Calibration Approach
- Follow PyGEM's recommended iterative calibration for marine-terminating glaciers
- Validate against independent datasets (stake observations) when possible
- Document model limitations and uncertainty sources
- Use appropriate statistical methods for uncertainty quantification

## 🎯 Dixon Glacier Specific Considerations

### Local Context
- Dixon Glacier is in Alaska (RGI region 01)
- Check for marine-terminating characteristics requiring frontal ablation calibration
- Validate elevation ranges against known Dixon Glacier topography
- Consider seasonal variations in mass balance patterns

### Available Data Integration Strategy
- **Primary Calibration**: surface_change_2022_2023.TIF for geodetic mass balance calibration
- **Independent Validation**: stake_observations_dixon.csv (2022-2025) for model validation
- Cross-reference calibrated parameters with regional climate patterns
- Consider debris cover effects if applicable

## 🚨 Critical Warnings

- **Never use placeholder or estimated values** in place of missing model outputs
- **Always verify file integrity** before using in analysis
- **Document all assumptions** and their scientific basis
- **Flag uncertainties explicitly** rather than presenting uncertain results as definitive
- **Stop execution** if critical data is missing or corrupted

## 📝 Progress Tracking Template

```markdown
## Current Status: [Stage Name]
**Last Updated**: [Timestamp]
**Completed Steps**:
- [ ] Task 1
- [ ] Task 2

**Next Steps**:
1. [Specific action with timeline]
2. [Next action with dependencies]

**Blockers/Issues**:
- [Any impediments to progress]

**Files Modified/Created**:
- [List with descriptions]

**Tools/Agents Used**:
- [Document which Claude Code tools and MCP servers were utilized]
```

---

*This document should be updated as workflows evolve and new best practices are identified through PyGEM model usage.*