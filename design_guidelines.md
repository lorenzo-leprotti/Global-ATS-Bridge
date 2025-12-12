# Design Guidelines: ULISSE (Global ATS Bridge)

## Design Approach

**Selected Approach:** Custom Professional/Financial Services Design
- Inspired by Goldman Sachs and premium financial service platforms
- Emphasis on trust, privacy, and professional credibility
- Clean, serious, data-focused aesthetic that conveys expertise

## Core Design Principles

1. **Privacy First:** Every design element reinforces zero-data-retention messaging
2. **Professional Authority:** Design conveys expertise in international-to-US resume conversion
3. **Clarity Over Creativity:** Function drives form; this is a utility tool, not a marketing site
4. **Trust Through Transparency:** Show the process, show the changes, show the privacy audit

## Typography

**Font Families:**
- Primary: Georgia (serif) - conveys professionalism and authority
- Fallback: Times New Roman
- Monospace: Consolas or Monaco for technical details (session IDs, file sizes)

**Hierarchy:**
- H1 (App Title): 32px, bold, uppercase, letter-spacing: 2px
- H2 (Section Headers): 24px, bold, normal case
- H3 (Subsections): 18px, semibold
- Body: 16px, regular, line-height: 1.6
- Small/Meta Text: 14px (privacy badges, timestamps)
- Button Text: 14px, bold, uppercase, letter-spacing: 1px

## Layout System

**Spacing Units:** Use increments of 8px (Tailwind: 2, 4, 6, 8, 12, 16, 20, 24, 32)
- Component padding: p-8 to p-12
- Section spacing: py-12 to py-20
- Element gaps: gap-4 to gap-8
- Form element spacing: space-y-6

**Container:**
- Max width: 1200px for main content area
- Two-column preview: 50/50 split with divider
- Single column for upload/processing (max-w-2xl, centered)

## Component Library

### Navigation/Header
- Minimal header: Logo/app name on left, privacy badge on right
- Sticky top bar with subtle shadow on scroll
- Height: 80px

### File Upload Zone
- Large dropzone area (min-height: 200px)
- Dashed border (2px, black) on idle
- Solid border on hover/drag-over
- Upload icon (48px) centered above text
- Accept indicator: "PDF only • Max 10MB"

### Dropdown Selector (Work Authorization)
- Clean, native-style select with custom arrow
- Full width within container
- Border: 2px solid black
- Padding: 12px 16px
- Focus state: increased border width to 3px

### Radio Buttons (Output Format)
- Large click targets (24px radio circles)
- Black fill when selected
- Label to the right, 16px font
- Horizontal layout with gap-8

### Primary Button
- Background: #1a1a1a (black)
- Text: #FFFFFF (white)
- Padding: 16px 48px
- Border-radius: 2px (minimal rounding)
- Uppercase text, bold
- Hover: #333333 background
- Disabled: #CCCCCC background

### Privacy Badge
- Background: #F5F5F5 (light gray)
- Small lock icon (16px) + text
- Padding: 8px 16px
- Border-radius: 4px
- Display inline-flex
- Font size: 14px

### Progress Indicator
- Linear progress bar (height: 4px, black)
- Checklist format below with checkmarks
- Each step: Icon (16px) + Text
- Completed steps: Black checkmark
- Current step: Pulsing indicator
- Pending steps: Gray text

### Comparison View (Two-Column)
- Vertical divider: 1px solid #E5E5E5
- Column headers: "ORIGINAL" | "OPTIMIZED"
- Issue badges: Warning icon + red/orange accent for problems
- Success badges: Checkmark + green accent for fixes
- Scrollable content areas (max-height: 600px)

### Alert/Error Messages
- Error: Red left border (4px) with light red background
- Warning: Orange left border with light orange background  
- Success: Green left border with light green background
- Padding: 16px 20px
- Close button (X) in top-right

### Privacy Audit Display
- Timestamp format: "2:34 PM EST"
- Monospace font for session ID
- List format with bullet points or checkmarks
- Light gray background panel
- Font size: 14px

## Visual Specifications

**Colors:** (Already specified by user, maintaining as-is)
- Background: #FFFFFF
- Primary Text: #000000
- Accent/Buttons: #1a1a1a
- Badge Background: #F5F5F5
- Borders: #000000 or #E5E5E5 (subtle)
- Error: #DC2626
- Warning: #F59E0B
- Success: #10B981

**Shadows:**
- Cards/Modals: 0 2px 8px rgba(0,0,0,0.1)
- Buttons (hover): 0 4px 12px rgba(0,0,0,0.15)
- Header (scroll): 0 2px 4px rgba(0,0,0,0.05)

**Borders:**
- Default: 2px solid #000000
- Subtle dividers: 1px solid #E5E5E5
- Input focus: 3px solid #000000

## Page Structure

**Landing/Main View:**
1. Header with app name and privacy badge
2. Hero title + subtitle (centered)
3. Upload zone (centered, max-w-2xl)
4. Work authorization dropdown
5. Output format radio buttons
6. Primary CTA button
7. Footer with minimal links

**Processing View:**
- Replace upload section with progress indicator
- Maintain header
- Center-aligned progress checklist
- Estimated time remaining (optional)

**Results View:**
- Header remains
- Two-column layout (Original | Optimized)
- Sticky download button (bottom-right or top-right)
- Privacy audit panel below comparison
- "Process Another" secondary button

## Interactions & Animations

**Minimal Animation Philosophy:**
- File upload: Fade-in of success checkmark (0.3s)
- Progress bar: Smooth width transition (0.5s ease)
- Step completion: Quick checkmark scale animation (0.2s)
- Button hover: Subtle background color transition (0.2s)
- NO complex scroll animations
- NO unnecessary motion effects

## Accessibility

- All form inputs have visible labels
- High contrast maintained (black on white)
- Focus indicators: 3px solid border
- Keyboard navigation supported for all interactions
- ARIA labels for icon-only buttons
- Alt text for privacy/trust badges

## Content Strategy

**Messaging Tone:** Professional, reassuring, transparent
- Emphasize privacy at every step
- Use precise technical language ("RAM-only processing", "ATS-compliant")
- Show, don't tell (actual privacy audit, real-time progress)
- Avoid marketing fluff - be direct and honest

**Trust Signals:**
- Privacy protocol badge (prominent)
- Real-time privacy audit display
- Session expiration timer
- No account/signup required messaging
- Technical transparency (session IDs, timestamps)

## Images

**No hero image** - This is a utility tool, not a marketing site. The interface should be clean and functional from the start.

**Icons Only:**
- Lock icon for privacy badges (16px)
- Upload/document icon for file uploader (48px)
- Checkmark icons for progress steps (16px)
- Warning/error icons for alerts (20px)
- Download icon for CTA button (20px)

Use Heroicons (outline style) for all icons via CDN.