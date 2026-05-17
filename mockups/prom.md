You are a senior UI/UX developer. Refactor the frontend of this mockup to match 
the visual language of official Colombian government digital platforms 
(gov.co ecosystem, Ministerio del Interior, Ministerio de Cultura).

## Context
This is a platform for indigenous community management in Colombia, 
under the scope of the Ministerio del Interior / Ministerio de Cultura. 
The interface must feel OFFICIAL, TRUSTWORTHY, and CULTURALLY RESPECTFUL.

## Design Direction: "Institutional Colombia with Indigenous Identity"

### Color Palette (strictly follow this)
- Primary: #B22222 (institutional red, like gov.co)
- Secondary: #1A3A5C (deep governmental navy)
- Accent warm: #C8922A (gold/ochre, representing indigenous craft/tierra)
- Background: #F5F5F0 (warm off-white, not pure white)
- Surface: #FFFFFF
- Text primary: #1C1C1C
- Text secondary: #4A4A4A
- Border: #D4D0C8

### Typography
- Headings: 'Playfair Display' (serif, institutional authority)
- Body/UI: 'Source Sans 3' (legible, government-grade)
- Load both from Google Fonts

### Layout & Visual Rules
1. Top navigation bar: solid #1A3A5C with the Colombian gov.co escudo aesthetic
   - Left: app logo + platform name in white
   - Right: user info + logout
   - Thin gold (#C8922A) bottom border on navbar

2. Sidebar (if present): #F0EDE6 background, left border accent #B22222
   - Icons + labels, active state with red left indicator bar

3. Cards/panels: white background, subtle shadow (0 2px 8px rgba(0,0,0,0.08))
   - Top accent border in red (#B22222) for primary cards
   - Rounded corners: 4px only (government sites are angular, not bubbly)

4. Buttons:
   - Primary: #B22222 background, white text, no border-radius > 4px
   - Secondary: outline #1A3A5C
   - Hover states: darken 10%, smooth 200ms transition

5. Tables (if any): alternating rows #FFFFFF / #F9F7F4, header #1A3A5C with white text

6. Forms: clean labels above inputs, border #D4D0C8, focus ring #B22222

7. Subtle indigenous pattern: add a decorative SVG geometric border/divider 
   inspired by Colombian indigenous textile patterns (Wayúu, Nasa, Zenú geometric motifs)
   — use as section dividers or header accents only, NOT overwhelming the UI

8. Footer (if applicable): #1A3A5C background, white text, Colombian coat of arms reference

### Tone
- NO rounded pill buttons
- NO purple/violet anywhere
- NO gradient hero sections
- NO playful animations — only functional micro-transitions (200ms ease)
- YES to formal whitespace
- YES to clear visual hierarchy
- YES to accessibility (contrast ratios AA minimum)

### Specific refactor tasks
- Apply the full color system replacing any placeholder/default colors
- Replace generic fonts with the specified typography pair
- Add the indigenous geometric divider as an SVG component/element
- Ensure the navbar matches gov.co institutional style
- Make all interactive states (hover, focus, active) consistent
- Ensure the layout feels like Colombia's official digital government portals

Output clean, well-commented code. Maintain the existing functionality — 
only improve the visual design layer.