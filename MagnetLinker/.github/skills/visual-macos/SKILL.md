## Tahoe 26 Design Language: Liquid Glass

**Core Philosophy**: Content-first with translucent "floating" controls that reflect/refract underlying content. Unified across Apple platforms (visionOS-inspired). Dynamic, fluid motion like real liquid glass.[web:109][web:110]

### Key Visual Principles
| Element | Description | Implementation |
|---------|-------------|----------------|
| **Liquid Glass** | Translucent material with real-time reflections, refractions, highlights. Behaves like glass (bends light). | `NSVisualEffectView` (AppKit), rgba opacity + blur shaders (others). Alpha 0.8-0.95. |
| **Transparency** | Transparent menu bar, sidebars/toolbars tint/reflect content underneath. Larger screen feel. | `titlebarAppearsTransparent=True`, `blendingMode=BehindWindowLayer`. |
| **Depth & Motion** | Subtle parallax, morphing animations. Controls "materialize" in/out. | Layer shadows, `cornerRadius=16px`, ease-in/out transitions. |
| **Icons/Widgets** | Rounded, customizable: light/dark/clear/tinted. Vibrant SF Symbols. | System icons + hue shift (Pillow/PyQt tint). Styles: monochrome, emoji folders. |
| **Colors** | System tints (#0B67FE blue), adaptive gradients. No glass-on-glass stacking. | `NSColor.systemBlue`, rgba(250,250,251,0.9) light glass. |
| **Typography** | SF Pro Display (bold/medium), larger content focus. | `NSFont.systemFontOfSize_weight_(28, "bold")`. |
| **Controls** | Floating layer over content. Rounded 12-20px, spaced/grouped. | Grouped buttons, no overlapping glass. Hover vibrancy. |
| **Themes** | Dynamic system/light/dark + accent tint color. | `setAppearanceMode("system")`. |

### Do's & Don'ts
- **Do**: Prioritize content (minimal chrome), use native blur, tint to match content.
- **Don't**: Stack multiple glass layers, hard shadows, flat colors—embrace fluidity.[web:106]
- **Motion**: Smooth morphing between states (toolbar→menu).[web:109]

**AppKit Native**: Auto-adapts to Tahoe (e.g., `NSVisualEffectMaterialHudWindow`). Others approximate with shaders/rgba.
