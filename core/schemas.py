"""Strict output contracts shared by the local prompt pipeline."""
from pydantic import BaseModel, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

class StructuredAnalysis(StrictModel):
    subjects: list[str]
    primary_subject: str
    appearance: str
    face: str
    expression: str
    clothing: str
    accessories: str
    pose: str
    environment: str
    foreground: str
    background: str
    composition: str
    camera_angle: str
    shot_type: str
    lens_estimate: str
    depth_of_field: str
    lighting: str
    colors: str
    materials: str
    textures: str
    style: str
    atmosphere: str
    hair: str
    body_orientation: str
    object_positions: str

class CharacterDNA(StrictModel):
    species: str
    body: str
    face: str
    eyes: str
    hair_fur: str
    skin: str
    clothing: str
    accessories: str
    unique_features: str

class GeneratedPrompt(StrictModel):
    prompt: str
    negative_prompt: str
