"""
Scenario Validator

This module provides validation for cyber range scenario JSON files.
It performs both schema validation and semantic validation to ensure
scenarios are well-formed and can be deployed.

Validation Types:
1. JSON Schema validation (structure, types, required fields)
2. Semantic validation (host references, network consistency, flag placement)
3. Enum enforcement (difficulty, vulnerability types, etc.)
4. Dependency checking (ensure all references are valid)

Example:
    >>> validator = ScenarioValidator()
    >>> result = validator.validate_file("scenario.json")
    >>> if result.is_valid:
    ...     print("Scenario is valid!")
    ... else:
    ...     for error in result.errors:
    ...         print(f"Error: {error}")
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error"""
    path: str
    message: str
    severity: str = "error"  # "error", "warning"
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Result of scenario validation"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def get_all_issues(self) -> List[ValidationError]:
        """Get all errors and warnings combined"""
        return self.errors + self.warnings


class ScenarioValidator:
    """
    Validates cyber range scenario JSON files.
    
    Performs comprehensive validation including:
    - JSON Schema validation
    - Semantic validation (references, topology)
    - Enum enforcement
    - Dependency checking
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize validator
        
        Args:
            schema_path: Path to JSON schema file. If None, uses default.
        """
        if schema_path is None:
            # Default to schema/scenario.schema.json
            schema_path = Path(__file__).parent.parent.parent / "schema" / "scenario.schema.json"
        
        self.schema_path = schema_path
        self.schema = self._load_schema()
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file"""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load schema from {self.schema_path}: {e}")
    
    def validate_file(self, scenario_path: Path) -> ValidationResult:
        """
        Validate a scenario JSON file
        
        Args:
            scenario_path: Path to scenario JSON file
            
        Returns:
            ValidationResult with errors and warnings
        """
        try:
            with open(scenario_path, 'r') as f:
                scenario = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError("", f"Invalid JSON: {e}", "error")],
                warnings=[]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError("", f"Failed to read file: {e}", "error")],
                warnings=[]
            )
        
        return self.validate(scenario)
    
    def validate(self, scenario: Dict[str, Any]) -> ValidationResult:
        """
        Validate a scenario dictionary
        
        Args:
            scenario: Scenario data as dictionary
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        # 1. JSON Schema validation
        schema_errors = self._validate_schema(scenario)
        errors.extend(schema_errors)
        
        # If schema validation fails, don't continue with semantic validation
        if schema_errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # 2. Semantic validation
        semantic_errors, semantic_warnings = self._validate_semantics(scenario)
        errors.extend(semantic_errors)
        warnings.extend(semantic_warnings)
        
        # 3. Network topology validation
        topo_errors, topo_warnings = self._validate_topology(scenario)
        errors.extend(topo_errors)
        warnings.extend(topo_warnings)
        
        # 4. Flag placement validation
        flag_errors, flag_warnings = self._validate_flags(scenario)
        errors.extend(flag_errors)
        warnings.extend(flag_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_schema(self, scenario: Dict[str, Any]) -> List[ValidationError]:
        """Validate against JSON schema"""
        errors: List[ValidationError] = []
        
        try:
            jsonschema.validate(instance=scenario, schema=self.schema)
        except jsonschema.ValidationError as e:
            # Extract path
            path = ".".join(str(p) for p in e.path) if e.path else "root"
            errors.append(ValidationError(
                path=path,
                message=e.message,
                severity="error"
            ))
        except jsonschema.SchemaError as e:
            errors.append(ValidationError(
                path="schema",
                message=f"Invalid schema: {e.message}",
                severity="error"
            ))
        
        return errors
    
    def _validate_semantics(self, scenario: Dict[str, Any]) -> tuple[List[ValidationError], List[ValidationError]]:
        """Validate semantic correctness (references, dependencies)"""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        # Extract IDs
        network_ids = {net["id"] for net in scenario.get("networks", [])}
        host_ids = {host["id"] for host in scenario.get("hosts", [])}
        flag_ids = {flag["id"] for flag in scenario.get("flags", [])}
        
        # Validate host references
        for idx, host in enumerate(scenario.get("hosts", [])):
            host_id = host.get("id", f"host_{idx}")
            
            # Check network references (networks is array of objects with network_id)
            for net_idx, net_ref in enumerate(host.get("networks", [])):
                if isinstance(net_ref, dict):
                    net_id = net_ref.get("network_id")
                    if net_id and net_id not in network_ids:
                        errors.append(ValidationError(
                            path=f"hosts[{idx}].networks[{net_idx}]",
                            message=f"Host '{host_id}' references unknown network '{net_id}'",
                            severity="error"
                        ))
            
            # Check flag references  
            for flag_id in host.get("flags", []):
                if flag_id not in flag_ids:
                    errors.append(ValidationError(
                        path=f"hosts[{idx}].flags",
                        message=f"Host '{host_id}' references unknown flag '{flag_id}'",
                        severity="error"
                    ))
            
            # Check if attacker host has flags (warning)
            if host.get("type") == "attacker" and host.get("flags"):
                warnings.append(ValidationError(
                    path=f"hosts[{idx}]",
                    message=f"Attacker host '{host_id}' has flags - this is unusual",
                    severity="warning"
                ))
        
        # Validate flag placement references
        for idx, flag in enumerate(scenario.get("flags", [])):
            flag_id = flag.get("id", f"flag_{idx}")
            placement = flag.get("placement", {})
            
            # Check host reference in placement
            host_id = placement.get("host_id")
            if host_id and host_id not in host_ids:
                errors.append(ValidationError(
                    path=f"flags[{idx}].placement.host_id",
                    message=f"Flag '{flag_id}' references unknown host '{host_id}'",
                    severity="error"
                ))
        
        # Validate vulnerability references (if they're defined separately)
        # In the schema, host.vulnerabilities is an array of strings (IDs)
        # Detailed vulnerability definitions are in top-level vulnerabilities array
        vulnerability_ids = {vuln.get("id") for vuln in scenario.get("vulnerabilities", [])}
        
        for idx, host in enumerate(scenario.get("hosts", [])):
            host_id = host.get("id", f"host_{idx}")
            
            for vuln_id in host.get("vulnerabilities", []):
                # If vulnerabilities array exists at top level, validate references
                if scenario.get("vulnerabilities") and vuln_id not in vulnerability_ids:
                    warnings.append(ValidationError(
                        path=f"hosts[{idx}].vulnerabilities",
                        message=f"Host '{host_id}' references undefined vulnerability '{vuln_id}'",
                        severity="warning"
                    ))
        
        return errors, warnings
    
    def _validate_topology(self, scenario: Dict[str, Any]) -> tuple[List[ValidationError], List[ValidationError]]:
        """Validate network topology"""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        networks = scenario.get("networks", [])
        hosts = scenario.get("hosts", [])
        
        # Check for at least one network
        if not networks:
            errors.append(ValidationError(
                path="networks",
                message="Scenario must have at least one network",
                severity="error"
            ))
        
        # Check for at least one host
        if not hosts:
            errors.append(ValidationError(
                path="hosts",
                message="Scenario must have at least one host",
                severity="error"
            ))
        
        # Check for attacker host
        attacker_hosts = [h for h in hosts if h.get("type") == "attacker"]
        if not attacker_hosts:
            warnings.append(ValidationError(
                path="hosts",
                message="No attacker host defined - scenario may not be solvable",
                severity="warning"
            ))
        elif len(attacker_hosts) > 1:
            warnings.append(ValidationError(
                path="hosts",
                message=f"Multiple attacker hosts defined ({len(attacker_hosts)}) - this is unusual",
                severity="warning"
            ))
        
        # Check for orphaned hosts (not connected to any network)
        for idx, host in enumerate(hosts):
            if not host.get("networks"):
                host_id = host.get("id", f"host_{idx}")
                warnings.append(ValidationError(
                    path=f"hosts[{idx}]",
                    message=f"Host '{host_id}' is not connected to any network",
                    severity="warning"
                ))
        
        # Check for used networks (networks is array of objects with network_id)
        used_networks = set()
        for host in hosts:
            for net_ref in host.get("networks", []):
                if isinstance(net_ref, dict):
                    net_id = net_ref.get("network_id")
                    if net_id:
                        used_networks.add(net_id)
        
        for idx, network in enumerate(networks):
            net_id = network.get("id", f"net_{idx}")
            if net_id not in used_networks:
                warnings.append(
                    ValidationError(
                        path=f"networks[{idx}]",
                        message=f"Network '{net_id}' is defined but not used by any host",
                        severity="warning",
                    )
                )
        
        return errors, warnings
    
    def _validate_flags(self, scenario: Dict[str, Any]) -> tuple[List[ValidationError], List[ValidationError]]:
        """Validate flag placement and configuration"""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        flags = scenario.get("flags", [])
        
        # Check for at least one flag
        if not flags:
            warnings.append(ValidationError(
                path="flags",
                message="Scenario has no flags - users won't have clear objectives",
                severity="warning"
            ))
            return errors, warnings
        
        # Check flag values are unique
        flag_values = []
        for idx, flag in enumerate(flags):
            value = flag.get("value")
            if value:
                if value in flag_values:
                    errors.append(
                        ValidationError(
                            path=f"flags[{idx}].value",
                            message=f"Duplicate flag value: '{value}'",
                            severity="error",
                        )
                    )
                flag_values.append(value)
        
        # Check flag IDs are unique
        flag_ids = []
        for idx, flag in enumerate(flags):
            flag_id = flag.get("id")
            if flag_id in flag_ids:
                errors.append(
                    ValidationError(
                        path=f"flags[{idx}].id",
                        message=f"Duplicate flag ID: '{flag_id}'",
                        severity="error",
                    )
                )
            flag_ids.append(flag_id)
        
        # Check flag placement validity
        for idx, flag in enumerate(flags):
            placement = flag.get("placement", {})
            placement_type = placement.get("type")
            
            # Validate placement has required fields
            if placement_type == "file":
                details = placement.get("details", {}) or {}
                file_path = placement.get("path") or details.get("path")
                if not file_path:
                    errors.append(
                        ValidationError(
                            path=f"flags[{idx}].placement",
                            message="File placement requires 'path' field",
                            severity="error",
                        )
                    )
            elif placement_type == "env_var":
                if not placement.get("variable"):
                    errors.append(ValidationError(
                        path=f"flags[{idx}].placement",
                        message="Environment variable placement requires 'variable' field",
                        severity="error"
                    ))
            elif placement_type == "db_row":
                details = placement.get("details", {})
                if not details.get("table") or not details.get("query"):
                    errors.append(ValidationError(
                        path=f"flags[{idx}].placement",
                        message="Database placement requires 'table' and 'query' in details",
                        severity="error"
                    ))
        
        return errors, warnings


def validate_scenario_file(scenario_path: Path) -> ValidationResult:
    """
    Convenience function to validate a scenario file
    
    Args:
        scenario_path: Path to scenario JSON file
        
    Returns:
        ValidationResult
    """
    validator = ScenarioValidator()
    return validator.validate_file(scenario_path)


def validate_scenario(scenario: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate a scenario dictionary
    
    Args:
        scenario: Scenario data as dictionary
        
    Returns:
        ValidationResult
    """
    validator = ScenarioValidator()
    return validator.validate(scenario)
