"""
SPEC §2.9 / F-0098 / US-38: Image Generation Provider Contract.
Defines interfaces and data structures for model-driven image generation,
provider registry cataloging, aspect ratio / dimensions resolution, and modular off-switch behavior.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional


@dataclass
class ImageModelDescriptor:
    """Descriptor for an available image generation model."""
    model_id: str
    provider: str
    supported_sizes: List[str]
    default_size: str = "1024x1024"
    supports_negative_prompt: bool = True
    supports_seed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "supported_sizes": self.supported_sizes,
            "default_size": self.default_size,
            "supports_negative_prompt": self.supports_negative_prompt,
            "supports_seed": self.supports_seed,
        }


@dataclass
class ImageGenerationRequest:
    """Request payload for generating an image."""
    prompt: str
    model: str = "openai/dall-e-3"
    size: str = "1024x1024"
    format: str = "png"
    quality: str = "standard"
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "model": self.model,
            "size": self.size,
            "format": self.format,
            "quality": self.quality,
            "negative_prompt": self.negative_prompt,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ImageGenerationRequest:
        return cls(
            prompt=data.get("prompt", ""),
            model=data.get("model", "openai/dall-e-3"),
            size=data.get("size", "1024x1024"),
            format=data.get("format", "png"),
            quality=data.get("quality", "standard"),
            negative_prompt=data.get("negative_prompt"),
            seed=data.get("seed"),
        )


@dataclass
class ImageGenerationResult:
    """Result of an image generation operation."""
    image_id: str
    b64_data: str
    mime_type: str
    format: str
    model_used: str
    prompt: str
    size: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "b64_data": self.b64_data,
            "mime_type": self.mime_type,
            "format": self.format,
            "model_used": self.model_used,
            "prompt": self.prompt,
            "size": self.size,
            "created_at": self.created_at,
        }


class BaseImageGenerationProvider(ABC):
    """
    Abstract interface for Image Generation Provider.
    Modular, swappable component per AGENTS.md law 11 and modularity architecture (03).
    """

    @abstractmethod
    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate an image from the given prompt and parameters."""
        pass

    @abstractmethod
    def list_models(self) -> List[ImageModelDescriptor]:
        """List registered image generation models."""
        pass

    @abstractmethod
    def is_model_supported(self, model_id: str) -> bool:
        """Check if an image model ID is supported."""
        pass
