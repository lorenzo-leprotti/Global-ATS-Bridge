import OpenAI from "openai";
import type { ParsedResume } from "@shared/schema";
import { parsedResumeSchema } from "@shared/schema";

// This is using Replit's AI Integrations service, which provides OpenAI-compatible API access without requiring your own API key.
const openai = new OpenAI({
  baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
  apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY
});

const SYSTEM_PROMPT = `You are a professional resume formatter specializing in converting international resumes to US ATS-compliant formats.

STRICT RULES:
1. Extract all information accurately from the source resume
2. Apply grade conversions using the provided table
3. Inject work authorization signal at the top
4. Maintain professional tone and original phrasing where appropriate
5. Remove all photos, graphics, and non-text elements
6. Output ONLY valid JSON matching the schema below

GRADE CONVERSION TABLE (Apply when detected):
- Italian 30L/30 or 110L/110: "GPA: 4.0/4.0 (Italian: [original])"
- Italian 30/30 or 105-110/110: "GPA: 3.9-4.0/4.0 (Italian: [original])"
- Italian 27-29/30 or 100-104/110: "GPA: 3.7-3.9/4.0 (Italian: [original])"
- Italian 24-26/30 or 90-99/110: "GPA: 3.0-3.5/4.0 (Italian: [original])"
- UK First-Class Honours: "GPA: 3.7-4.0/4.0 (UK: First-Class)"
- UK Upper Second (2:1): "GPA: 3.3-3.7/4.0 (UK: 2:1)"
- German "Sehr Gut" (1.0-1.5): "GPA: 3.8-4.0/4.0 (German: [original])"
- German "Gut" (1.6-2.5): "GPA: 3.0-3.7/4.0 (German: [original])"
- Indian First Division (60%+): "GPA: 3.5-4.0/4.0 (Indian: [original]%)"

ALWAYS append original grade system in parentheses for transparency.

OUTPUT SCHEMA:
{
  "personal_info": {
    "name": "string",
    "email": "string",
    "phone": "string (optional)",
    "location": "string (city, state format)",
    "linkedin": "string (optional)",
    "work_authorization": "string (from user input)"
  },
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field": "string",
      "location": "string",
      "dates": "MM/YYYY - MM/YYYY",
      "gpa": "string (converted if applicable)",
      "honors": "string (optional)"
    }
  ],
  "experience": [
    {
      "title": "string",
      "company": "string",
      "location": "string",
      "dates": "MM/YYYY - MM/YYYY or Present",
      "bullets": ["string array of 3-5 accomplishment bullets"]
    }
  ],
  "skills": {
    "technical": ["string array"],
    "languages": ["string array"],
    "certifications": ["string array (optional)"]
  },
  "projects": [
    {
      "name": "string",
      "description": "string",
      "technologies": ["string array"],
      "date": "MM/YYYY (optional)"
    }
  ]
}

FORMATTING REQUIREMENTS:
- Use action verbs (Led, Developed, Managed, etc.)
- Quantify achievements where possible (%, $, #)
- Keep bullets concise (1-2 lines max)
- Use past tense for previous roles, present for current
- Maintain chronological order (most recent first)`;

async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error | undefined;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;
      
      const isRetryable = 
        error.status === 429 || 
        error.status === 500 || 
        error.status === 502 || 
        error.status === 503 || 
        error.code === 'ECONNRESET' ||
        error.code === 'ETIMEDOUT';
      
      if (!isRetryable || attempt === maxRetries - 1) {
        throw error;
      }
      
      const delay = baseDelay * Math.pow(2, attempt) + Math.random() * 1000;
      console.log(`OpenAI request failed (attempt ${attempt + 1}/${maxRetries}), retrying in ${Math.round(delay)}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError || new Error("Max retries exceeded");
}

export async function parseResumeWithAI(
  resumeText: string,
  workAuthorization: string
): Promise<ParsedResume> {
  return retryWithBackoff(async () => {
    const response = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        {
          role: "user",
          content: `Parse the following resume and output structured JSON. The work authorization to include is: "${workAuthorization}"

RESUME TEXT:
${resumeText}`
        }
      ],
      response_format: { type: "json_object" },
      max_completion_tokens: 8192
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new Error("No response from AI");
    }

    const parsed = JSON.parse(content);
    
    if (!parsed.personal_info) {
      parsed.personal_info = { name: "", email: "", work_authorization: workAuthorization };
    }
    parsed.personal_info.work_authorization = workAuthorization;

    const validated = parsedResumeSchema.parse(parsed);
    return validated;
  });
}

export function validateParsedResume(resume: ParsedResume): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!resume.personal_info?.name) {
    errors.push("Missing required field: name");
  }
  if (!resume.personal_info?.email) {
    errors.push("Missing required field: email");
  }
  if (!resume.education || resume.education.length === 0) {
    errors.push("Missing required field: education");
  } else {
    if (!resume.education[0].institution) {
      errors.push("Missing required field: institution");
    }
    if (!resume.education[0].degree) {
      errors.push("Missing required field: degree");
    }
  }

  return { valid: errors.length === 0, errors };
}
