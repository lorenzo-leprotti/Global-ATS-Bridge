export type IndustryTemplate = "tech" | "finance" | "consulting" | "general";

export interface TemplateConfig {
  id: IndustryTemplate;
  name: string;
  description: string;
  sectionOrder: string[];
  emphasisKeywords: string[];
  formatting: {
    bulletStyle: "dash" | "dot" | "arrow";
    dateFormat: "full" | "short";
    includeLinkedin: boolean;
    skillsLayout: "inline" | "grouped";
  };
}

export const templates: Record<IndustryTemplate, TemplateConfig> = {
  tech: {
    id: "tech",
    name: "Technology",
    description: "Optimized for software engineering, data science, and tech roles",
    sectionOrder: ["skills", "experience", "projects", "education"],
    emphasisKeywords: [
      "Python", "JavaScript", "TypeScript", "React", "Node.js", "AWS", "Docker",
      "Kubernetes", "CI/CD", "Agile", "Scrum", "API", "REST", "GraphQL",
      "Machine Learning", "Data Science", "Cloud", "DevOps", "Git"
    ],
    formatting: {
      bulletStyle: "dash",
      dateFormat: "short",
      includeLinkedin: true,
      skillsLayout: "grouped"
    }
  },
  finance: {
    id: "finance",
    name: "Finance & Banking",
    description: "Tailored for investment banking, private equity, and financial services",
    sectionOrder: ["education", "experience", "skills", "projects"],
    emphasisKeywords: [
      "Financial Modeling", "Valuation", "DCF", "M&A", "LBO", "Due Diligence",
      "Bloomberg", "Excel", "VBA", "SQL", "Python", "Risk Management",
      "Portfolio Management", "Investment Analysis", "CFA", "Series 7"
    ],
    formatting: {
      bulletStyle: "dot",
      dateFormat: "full",
      includeLinkedin: true,
      skillsLayout: "inline"
    }
  },
  consulting: {
    id: "consulting",
    name: "Consulting",
    description: "Structured for management consulting and strategy roles",
    sectionOrder: ["education", "experience", "skills", "projects"],
    emphasisKeywords: [
      "Strategy", "Analysis", "Problem Solving", "Client Management",
      "Stakeholder", "ROI", "KPI", "Process Improvement", "Change Management",
      "PowerPoint", "Excel", "Data Analysis", "Project Management", "Leadership"
    ],
    formatting: {
      bulletStyle: "dot",
      dateFormat: "full",
      includeLinkedin: true,
      skillsLayout: "inline"
    }
  },
  general: {
    id: "general",
    name: "General",
    description: "Balanced format suitable for most industries",
    sectionOrder: ["experience", "education", "skills", "projects"],
    emphasisKeywords: [
      "Leadership", "Management", "Communication", "Teamwork", "Problem Solving",
      "Project Management", "Results", "Achievement", "Initiative", "Strategic"
    ],
    formatting: {
      bulletStyle: "dash",
      dateFormat: "short",
      includeLinkedin: true,
      skillsLayout: "grouped"
    }
  }
};

export function getTemplate(id: IndustryTemplate): TemplateConfig {
  return templates[id] || templates.general;
}

export function getAllTemplates(): TemplateConfig[] {
  return Object.values(templates);
}
