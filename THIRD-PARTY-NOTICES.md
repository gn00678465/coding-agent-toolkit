# Third-Party Notices

This repository includes material derived from third-party projects. Each entry
below records the upstream source, its license, and which files in this
repository are derived from it.

---

## old-coder

- **Upstream:** https://github.com/AmazingAng/old-coder
- **License:** MIT
- **Copyright:** Copyright (c) 2026 amazingang
- **Derived files:** `plugins/code-review/skills/verification-gate/`

The `verification-gate` skill adapts the GAUNTLET and EVIDENCE stages of the
`old-coder` skill into a standalone, workflow-independent verification gate.
The upstream SPEC approval loop, the RED/GREEN/REFACTOR development cycle, and
the independent-verification protocol are not included; the layer stack, the
fail-closed checker rules, the anti-gaming rules, and the evidence report
structure are.

Full upstream license text:

```
MIT License

Copyright (c) 2026 amazingang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
