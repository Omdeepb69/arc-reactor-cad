# **ARC Reactor CAD** ⚡

## DESCRIPTION

Alright geniuses, listen up. This is ARC Reactor CAD - your friendly neighborhood AI circuit sidekick. Think of it as J.A.R.V.I.S. for your Arduino projects. It helps you whip up, visualize, and even get tips on circuits using just prompts or pics. Pretty sick, right?

## FEATURES ✨

*   **Prompt-to-Circuit & Code:** Spill the tea on your Arduino dreams (like 'blink an LED' fam), and *poof* - circuit diagram and code appear. Magic? Nah, just good AI.
*   **Visual Circuit Builder (Pygame UI):** A simple drag-and-drop vibe using Pygame. Slap down components, wire 'em up visually. It's a proof of concept, not a full-blown physics sim, capiche?
*   **J.A.R.V.I.S. Jr. Suggestions:** This AI wingman checks your circuits (generated or IRL snaps) and drops suggestions. Think efficiency tweaks or maybe swapping parts. "Might I suggest Vibranium? ...Okay, maybe just standard issue." 😉
*   **Circuit Snapshot Analysis (Beta):** Yeet a pic of your breadboard or schematic. The AI tries to decode it and spit out Arduino code. Keep it simple for now, we're still dialing it in (scope: basic stuff, give it a week or three).
*   **Code Generation & Basic Simulation:** Get that sweet, sweet Arduino (.ino) code and watch a basic Pygame sim (like an LED blinking). It's alive! (Sort of).

## LEARNING BENEFITS 🧠

Level up your skills by mixing LLMs with UI dev (shoutout Pygame!), basic electronics, maybe some computer vision if you dabble in the snapshot feature. It's like building your own mini Stark Industries R&D lab, minus the flying suits (for now). Get that bread(board)! 🥖

## TECHNOLOGIES USED 💻

*   `pygame` (UI, basic viz/sim)
*   `requests` / `Gemini` (Talking to the big AI brains)
*   `Pillow` (PIL) (Image stuff)
*   `opencv-python` (Optional, for analyzing circuit pics)
*   `schemdraw` (Maybe later, if Pygame drawing gets too cray)

## SETUP AND INSTALLATION 🚀

Get this baby running. No excuses.

```bash
git clone https://github.com/Omdeepb69/arc-reactor-cad.git
cd arc-reactor-cad
pip install -r requirements.txt
# You might need an API key for the LLM, check the config!
```

## USAGE

Fire up the main script (`main.py` probably, check the code!). Tweak `config.json` if you need to change settings (like API keys, don't hardcode 'em, people!).

## PROJECT STRUCTURE 📁

Standard issue: `src/` for the good stuff (code), `tests/` for making sure it doesn't blow up (unit tests), and `docs/` if we ever write proper docs (lol).

## LICENSE

MIT License - Do whatever you want, just don't blame me if your toaster starts talking back.
