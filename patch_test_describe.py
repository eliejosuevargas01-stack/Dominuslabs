import re

with open("src/pages/omnichannelIdentity.test.ts", "r") as f:
    content = f.read()

# Remove the closing describe brace that was before our appended tests
content = content.replace("  });\n});\n\n  it('prioritizes", "  });\n\n  it('prioritizes")
content += "});\n"

with open("src/pages/omnichannelIdentity.test.ts", "w") as f:
    f.write(content)
