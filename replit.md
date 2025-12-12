# ULISSE - Global ATS Bridge

## Overview

ULISSE is a privacy-first web application that converts international resumes into US ATS-compliant formats. The tool helps international job seekers by:

- Converting foreign grade systems (Italian, UK, German, Indian) to US GPA equivalents
- Adding work authorization signals (F-1 OPT, H-1B, etc.) to resumes
- Reformatting resumes to pass Applicant Tracking Systems
- Generating output in PDF or DOCX format

The application processes uploaded PDF resumes using AI, applies grade conversions, and outputs reformatted documents. It emphasizes zero data retention and RAM-only processing for privacy.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter (lightweight alternative to React Router)
- **State Management**: TanStack React Query for server state
- **UI Components**: shadcn/ui component library with Radix primitives
- **Styling**: Tailwind CSS with custom design tokens following Goldman Sachs-inspired professional aesthetic
- **Build Tool**: Vite with hot module replacement

### Backend Architecture
- **Runtime**: Node.js with Express
- **Language**: TypeScript (ESM modules)
- **File Upload**: Multer for handling PDF uploads (memory storage, 10MB limit)
- **Session Management**: In-memory storage with UUID-based session IDs and 15-minute expiration
- **PDF Processing**: pdf-parse for text extraction
- **Document Generation**: PDFKit for PDF output, docx library for DOCX output

### AI Integration
- **Service**: Replit AI Integrations (OpenAI-compatible API)
- **Purpose**: Resume parsing and formatting via structured prompts
- **Output**: Validated JSON matching Zod schemas

### Data Flow
1. User uploads PDF resume with work authorization selection
2. Server extracts text using pdf-parse
3. AI parses and structures resume content
4. Grade conversion rules applied (Italian, UK, German, Indian systems)
5. Work authorization signal injected
6. Document generated in selected format (PDF/DOCX)
7. Session expires after 15 minutes, data purged from memory

### Database Schema
- Uses Drizzle ORM with PostgreSQL dialect
- Schema defined in `shared/schema.ts`
- Current implementation uses in-memory storage for sessions (privacy-first design)
- Database can be added for persistence if needed

### Key Design Decisions
- **In-memory storage**: Chosen over database for privacy (zero data retention)
- **Single-page application**: Simple workflow doesn't require complex routing
- **Zod validation**: Shared schemas between frontend and backend for type safety
- **Professional UI**: Georgia serif font, neutral colors, minimal design per design_guidelines.md

## External Dependencies

### AI Services
- Replit AI Integrations (OpenAI-compatible API via environment variables)
  - `AI_INTEGRATIONS_OPENAI_BASE_URL`
  - `AI_INTEGRATIONS_OPENAI_API_KEY`

### Database
- PostgreSQL via `DATABASE_URL` environment variable
- Drizzle ORM for schema management and queries

### NPM Packages (Key)
- **Frontend**: React, TanStack Query, Radix UI, Tailwind CSS, wouter
- **Backend**: Express, Multer, PDFKit, docx, pdf-parse, Zod
- **Shared**: Drizzle ORM, Zod for validation schemas