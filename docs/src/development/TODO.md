# 📝 Contribution Opportunities

Interested in contributing? Below are available tasks across different areas of the project. Feel free to reach out to @yulesxoxo for questions or guidance.

[![Discord Presence](https://lanyard.cnrad.dev/api/518169167048998913)](https://discord.com/users/518169167048998913)

---

## 🔧 Backend Development

### Android Multi-Touch Gesture Implementation (PoC)
**Library:** [uiautomator2](https://github.com/openatx/uiautomator2)

**Challenge:**  
ADB lacks native multi-touch gesture support. uiautomator2 offers:
- Coordinate-based tapping (`d.click(x, y)`)
- Screenshot capture (`d.screenshot()`)
- Advanced gestures (swipe, pinch, etc.)

**Goals:**
- Develop PoC for multi-touch gestures
- Prioritize pinch-to-zoom for game automation

**Extended Opportunities:**
1. Explore additional uiautomator2 game automation features
2. Performance comparison: uiautomator2 vs standard ADB
3. Benchmark tests for shared functionality (tap, screenshot, swipe)

___

### Desktop Client Support Investigation

**Current Understanding:**
1. Mouse click simulation limitations (requires actual cursor movement)
2. Screenshot challenges with display scaling/multi-monitor setups
3. Higher detection risk compared to ADB (if Lilith starts to care about botting)

**Implementation Needs:**
1. Device abstraction layer (Android vs Desktop)
2. Unified input mapping system
   ```python
   # The actual bot code should not end up looking like this.
   if device.platform == "Android":
   device.press_back_button()
   elif device.platform == "DesktopApp":
   device.keyboard.press("ESC")
   ```
3. Complete desktop interaction logic

---

## 🖥️ Frontend Development

### Global Hotkey Config Component
Create a Svelte Component to edit a single Global Hotkey in the config.  
You can decide what format it should be stored in, in the config too. 

___

### Custom Routine Component Upgrade
**Current:** Basic functionality implemented  
**Goal:** Enhanced drag-and-drop interface, or you might have better ideas?

**Design Opportunities:**
- UX/UI improvements
- Multi-routine management
- Intuitive drag-and-drop implementation

---

## 📖 Documentation

### Emulator Setup Guides
**Format:** Individual `.md` files per emulator

**Needed Guides:**
- BlueStacks
- MuMu Player
- LDPlayer
- MuMu Pro (Mac)
- BlueStacks Air (Mac)

**Guide Requirements:**
- Default device ID setup
- ADB enabling steps
- Recommended configuration
- Multi-instance device identification

___

### Physical Device Setup
**Topics Needed:**
- USB debugging activation
- Wireless debugging setup
- Device ID identification
- Display configuration
- Security best practices

___

### Custom Routine Documentation
**Content Needed:**
- Feature explanation and workflow
- Practical examples (AFK Journey reference)

---

## 🎮 AFK Journey Specific



### Arcane Labyrinth Optimization (Difficulty 15+)
**Goal:** Consistent Floor 16 clears

**Suggestions:**
- Coordinate with Arcane Lab channel for team comps
- Develop rune/crest priority system

___

### Fishing Mechanic
**Technical Notes:**
- Template matching likely insufficient
- Potential heatmap approach
- Input delay considerations (see debug info)

___

### Feature Documentation
**Scope:**
- Complete feature catalog
- Usage instructions
- Configuration options
- Visual examples

---

## 🚧 In Progress

- **GFL2 Daily Automation** - @valextr
- **Backend Refactor (Second Pass)** - @valextr

---

## 💬 Getting Help

- **Discord:** Use the badge above
- **GitHub:** Create issues for bugs/feature requests
