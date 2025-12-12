import { z } from "zod";

export const workAuthorizationOptions = [
  "F-1 OPT (Optional Practical Training)",
  "F-1 CPT (Curricular Practical Training)",
  "J-1 (Exchange Visitor)",
  "H-1B (Specialty Occupation)",
  "Green Card / Permanent Resident",
  "U.S. Citizen",
  "Require Sponsorship (Other)"
] as const;

export type WorkAuthorization = typeof workAuthorizationOptions[number];

export type OutputFormat = "pdf" | "docx";

export const educationSchema = z.object({
  institution: z.string(),
  degree: z.string(),
  field: z.string(),
  location: z.string(),
  dates: z.string(),
  gpa: z.string().optional(),
  honors: z.string().optional()
});

export const experienceSchema = z.object({
  title: z.string(),
  company: z.string(),
  location: z.string(),
  dates: z.string(),
  bullets: z.array(z.string())
});

export const projectSchema = z.object({
  name: z.string(),
  description: z.string(),
  technologies: z.array(z.string()),
  date: z.string().optional()
});

export const personalInfoSchema = z.object({
  name: z.string(),
  email: z.string(),
  phone: z.string().optional(),
  location: z.string().optional(),
  linkedin: z.string().optional(),
  work_authorization: z.string()
});

export const skillsSchema = z.object({
  technical: z.array(z.string()).optional(),
  languages: z.array(z.string()).optional(),
  certifications: z.array(z.string()).optional()
});

export const parsedResumeSchema = z.object({
  personal_info: personalInfoSchema,
  education: z.array(educationSchema),
  experience: z.array(experienceSchema),
  skills: skillsSchema.optional(),
  projects: z.array(projectSchema).optional()
});

export type Education = z.infer<typeof educationSchema>;
export type Experience = z.infer<typeof experienceSchema>;
export type Project = z.infer<typeof projectSchema>;
export type PersonalInfo = z.infer<typeof personalInfoSchema>;
export type Skills = z.infer<typeof skillsSchema>;
export type ParsedResume = z.infer<typeof parsedResumeSchema>;

export interface DetectedIssue {
  type: "warning" | "info";
  original: string;
  description: string;
}

export interface AppliedChange {
  type: "fix" | "enhancement";
  description: string;
  before?: string;
  after?: string;
}

export interface ProcessingSession {
  id: string;
  uploadedAt: string;
  processedAt?: string;
  expiresAt: string;
}

export interface ResumeProcessingResult {
  success: boolean;
  session: ProcessingSession;
  originalText?: string;
  parsedResume?: ParsedResume;
  detectedIssues?: DetectedIssue[];
  appliedChanges?: AppliedChange[];
  error?: string;
  extractionPercentage?: number;
}

export interface UploadRequest {
  workAuthorization: WorkAuthorization;
  outputFormat: OutputFormat;
}

export interface ProcessingStep {
  id: string;
  label: string;
  status: "pending" | "processing" | "completed" | "error";
}
