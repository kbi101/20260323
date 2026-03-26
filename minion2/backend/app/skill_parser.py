import re
import os
from typing import List, Dict, Optional
from pydantic import BaseModel

class SkillPhase(BaseModel):
    name: str
    instruction: str

class Skill(BaseModel):
    name: str = ""
    persona: str = ""
    tools: List[str] = []
    phases: List[SkillPhase] = []

def parse_skill(file_path: str) -> Skill:
    if not os.path.exists(file_path):
        return Skill()
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.split("\n")
    skill = Skill()
    current_section = ""
    
    for line in lines:
        if line.startswith("# "):
            skill.name = line.replace("# ", "").strip()
        elif line.startswith("## Persona"):
            current_section = "persona"
            continue
        elif line.startswith("## Tools"):
            current_section = "tools"
            continue
        elif line.startswith("## Phases"):
            current_section = "phases"
            continue
        elif current_section == "persona" and line.strip():
            skill.persona += line.strip() + " "
        elif current_section == "tools" and line.strip().startswith("- "):
            skill.tools.append(line.replace("- ", "").strip())
        elif current_section == "phases":
            # Match 1. **Name**: Instruction
            match = re.match(r"^\d+\.\s+\*\*(.+?)\*\*:\s*(.+)$", line.strip())
            if match:
                skill.phases.append(SkillPhase(name=match.group(1), instruction=match.group(2)))
                
    skill.persona = skill.persona.strip()
    return skill
