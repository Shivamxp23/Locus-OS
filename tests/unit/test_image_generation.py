"""
Unit tests for Image Generation Provider (SPEC §2.9, F-0098, US-38).
"""
import pytest

from sidecar.image_generation import (
    DEFAULT_IMAGE_MODELS,
    ImageGenerationProvider,
    TINY_PNG_B64,
)
from sidecar.providers.image_generation import (
    BaseImageGenerationProvider,
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageModelDescriptor,
)
from sidecar.registry import get_registry


class TestImageGenerationProvider:
    """Test image generation provider functionality per SPEC §2.9."""

    def test_list_models_returns_registered_catalog(self):
        """SPEC §2.9 line 2648: '## Feature §2.9: Image Generation'"""
        provider = ImageGenerationProvider()
        models = provider.list_models()
        assert len(models) >= 4
        model_ids = {m.model_id for m in models}
        assert "openai/dall-e-3" in model_ids
        assert "google/imagen-3.0" in model_ids
        assert "stability/sd3-turbo" in model_ids
        assert "black-forest-labs/flux-1.1-pro" in model_ids

    def test_inherited_pi_image_models_compatibility(self):
        """SPEC §2.9 line 2649: '- **Verdict**: 📦 KEEP-PI · **Source**: pi/images.ts · **Repo vs .locus**: locus-os (inherited)'"""
        provider = ImageGenerationProvider()
        assert provider.is_model_supported("openai/dall-e-3") is True
        assert provider.is_model_supported("google/imagen-3.0") is True
        assert provider.is_model_supported("non-existent-image-model") is False

    def test_generate_image_success(self):
        """SPEC §2.9 line 2651: '- **Scope**: Built-in image provider registry. Inherited unchanged.'"""
        provider = ImageGenerationProvider()
        req = ImageGenerationRequest(
            prompt="A futuristic solar punk treehouse in pristine forest",
            model="openai/dall-e-3",
            size="1024x1024",
            format="png",
        )
        res = provider.generate_image(req)
        assert isinstance(res, ImageGenerationResult)
        assert res.prompt == "A futuristic solar punk treehouse in pristine forest"
        assert res.model_used == "openai/dall-e-3"
        assert res.size == "1024x1024"
        assert res.mime_type == "image/png"
        assert res.b64_data == TINY_PNG_B64
        assert res.image_id.startswith("img_")

    def test_generate_image_empty_prompt_raises(self):
        """SPEC §2.9 line 2651: 'Built-in image provider registry: prompt validation'"""
        provider = ImageGenerationProvider()
        req_empty = ImageGenerationRequest(prompt="")
        with pytest.raises(ValueError, match="cannot be empty"):
            provider.generate_image(req_empty)

        req_whitespace = ImageGenerationRequest(prompt="    ")
        with pytest.raises(ValueError, match="cannot be empty"):
            provider.generate_image(req_whitespace)

    def test_unsupported_size_normalizes_to_default(self):
        """SPEC §2.9 line 2651: 'Built-in image provider registry: size normalization'"""
        provider = ImageGenerationProvider()
        req = ImageGenerationRequest(
            prompt="A cozy reading nook",
            model="openai/dall-e-3",
            size="999x999",  # Unsupported
        )
        res = provider.generate_image(req)
        # Normalizes to 1024x1024 default size for dall-e-3
        assert res.size == "1024x1024"

    def test_modular_off_switch_raises_runtime_error(self):
        """SPEC §2.9 line 2650: '- **Off state**: Disable via locus.images.enabled'"""
        provider_disabled = ImageGenerationProvider(
            custom_config={"locus.image_generation.enabled": False}
        )
        assert provider_disabled.is_enabled() is False

        req = ImageGenerationRequest(prompt="A test prompt")
        with pytest.raises(RuntimeError, match="disabled via locus.image_generation.enabled"):
            provider_disabled.generate_image(req)

    def test_provider_registry_entry(self):
        """SPEC §2.9 Criteria 2: 'Registers as a provider in sidecar/providers/ with modular off-switch'"""
        registry = get_registry()
        prov_cls = registry.get_active_provider("image_generation")
        assert prov_cls is not None
        instance = prov_cls()
        assert isinstance(instance, BaseImageGenerationProvider)
