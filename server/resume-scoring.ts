import type { ParsedResume } from "@shared/schema";
import type { IndustryTemplate, TemplateConfig } from "./templates";
import { getTemplate } from "./templates";

export interface ScoreBreakdown {
  category: string;
  score: number;
  maxScore: number;
  suggestions: string[];
}

export interface ResumeScore {
  overallScore: number;
  grade: "A" | "B" | "C" | "D" | "F";
  breakdown: ScoreBreakdown[];
  topSuggestions: string[];
}

function countQuantifiedAchievements(bullets: string[]): number {
  const quantifiedPattern = /\b(\d+%|\$\d+|\d+x|\d+\+|\d+ (million|thousand|hundred|users|customers|clients|projects|team members))/i;
  return bullets.filter(bullet => quantifiedPattern.test(bullet)).length;
}

function countActionVerbs(bullets: string[]): number {
  const actionVerbs = [
    "achieved", "built", "created", "delivered", "developed", "drove", "established",
    "executed", "generated", "implemented", "improved", "increased", "launched",
    "led", "managed", "optimized", "reduced", "resolved", "spearheaded", "streamlined"
  ];
  const pattern = new RegExp(`^(${actionVerbs.join("|")})\\b`, "i");
  return bullets.filter(bullet => pattern.test(bullet.trim())).length;
}

function countKeywordMatches(resume: ParsedResume, keywords: string[]): number {
  const resumeText = JSON.stringify(resume).toLowerCase();
  return keywords.filter(keyword => resumeText.includes(keyword.toLowerCase())).length;
}

export function scoreResume(resume: ParsedResume, templateId: IndustryTemplate = "general"): ResumeScore {
  const template = getTemplate(templateId);
  const breakdown: ScoreBreakdown[] = [];
  
  // 1. Contact Information (10 points)
  const contactSuggestions: string[] = [];
  let contactScore = 0;
  
  if (resume.personal_info.name) contactScore += 2;
  else contactSuggestions.push("Add your full name");
  
  if (resume.personal_info.email) contactScore += 3;
  else contactSuggestions.push("Add a professional email address");
  
  if (resume.personal_info.phone) contactScore += 2;
  else contactSuggestions.push("Add a phone number");
  
  if (resume.personal_info.location) contactScore += 2;
  else contactSuggestions.push("Add your location (city, state)");
  
  if (resume.personal_info.linkedin) contactScore += 1;
  else if (template.formatting.includeLinkedin) {
    contactSuggestions.push("Add your LinkedIn profile URL");
  }
  
  breakdown.push({
    category: "Contact Information",
    score: contactScore,
    maxScore: 10,
    suggestions: contactSuggestions
  });

  // 2. Work Experience (30 points)
  const expSuggestions: string[] = [];
  let expScore = 0;
  
  const experiences = resume.experience || [];
  if (experiences.length >= 2) expScore += 8;
  else if (experiences.length === 1) {
    expScore += 4;
    expSuggestions.push("Add more work experience if available");
  } else {
    expSuggestions.push("Add at least one work experience entry");
  }
  
  const allBullets = experiences.flatMap(exp => exp.bullets || []);
  const totalBullets = allBullets.length;
  
  if (totalBullets >= 8) expScore += 6;
  else if (totalBullets >= 4) expScore += 3;
  else expSuggestions.push("Add more bullet points describing your achievements");
  
  const quantified = countQuantifiedAchievements(allBullets);
  if (quantified >= 5) expScore += 8;
  else if (quantified >= 2) expScore += 4;
  else expSuggestions.push("Add metrics and numbers to quantify your achievements (e.g., 'Increased sales by 25%')");
  
  const actionVerbCount = countActionVerbs(allBullets);
  if (actionVerbCount >= totalBullets * 0.7) expScore += 8;
  else if (actionVerbCount >= totalBullets * 0.4) expScore += 4;
  else expSuggestions.push("Start bullet points with strong action verbs (e.g., 'Led', 'Developed', 'Achieved')");
  
  breakdown.push({
    category: "Work Experience",
    score: expScore,
    maxScore: 30,
    suggestions: expSuggestions
  });

  // 3. Education (15 points)
  const eduSuggestions: string[] = [];
  let eduScore = 0;
  
  const education = resume.education || [];
  if (education.length >= 1) {
    eduScore += 5;
    
    const hasGPA = education.some(edu => edu.gpa && parseFloat(edu.gpa) > 0);
    if (hasGPA) eduScore += 5;
    else eduSuggestions.push("Consider adding your GPA if it's 3.0 or higher");
    
    const hasDates = education.every(edu => edu.dates);
    if (hasDates) eduScore += 3;
    else eduSuggestions.push("Add graduation dates to your education entries");
    
    const hasHonors = education.some(edu => edu.honors);
    if (hasHonors) eduScore += 2;
  } else {
    eduSuggestions.push("Add your educational background");
  }
  
  breakdown.push({
    category: "Education",
    score: eduScore,
    maxScore: 15,
    suggestions: eduSuggestions
  });

  // 4. Skills (20 points)
  const skillsSuggestions: string[] = [];
  let skillsScore = 0;
  
  const skills = resume.skills;
  if (skills) {
    const technicalCount = skills.technical?.length || 0;
    if (technicalCount >= 8) skillsScore += 10;
    else if (technicalCount >= 4) skillsScore += 5;
    else skillsSuggestions.push("Add more technical skills relevant to your target role");
    
    const keywordMatches = countKeywordMatches(resume, template.emphasisKeywords);
    if (keywordMatches >= 5) skillsScore += 10;
    else if (keywordMatches >= 2) skillsScore += 5;
    else skillsSuggestions.push(`Add industry-specific keywords for ${template.name} roles`);
  } else {
    skillsSuggestions.push("Add a skills section highlighting your technical and professional abilities");
  }
  
  breakdown.push({
    category: "Skills & Keywords",
    score: skillsScore,
    maxScore: 20,
    suggestions: skillsSuggestions
  });

  // 5. Projects & Extras (15 points)
  const projectsSuggestions: string[] = [];
  let projectsScore = 0;
  
  const projects = resume.projects || [];
  if (projects.length >= 2) {
    projectsScore += 8;
  } else if (projects.length === 1) {
    projectsScore += 4;
    projectsSuggestions.push("Add more projects to showcase your work");
  } else {
    projectsSuggestions.push("Add relevant projects to demonstrate your skills");
  }
  
  const projectsWithTech = projects.filter(p => p.technologies && p.technologies.length > 0).length;
  if (projectsWithTech >= projects.length * 0.8) projectsScore += 4;
  else projectsSuggestions.push("List technologies used for each project");
  
  const projectsWithDesc = projects.filter(p => p.description && p.description.length > 30).length;
  if (projectsWithDesc >= projects.length * 0.8) projectsScore += 3;
  else projectsSuggestions.push("Add detailed descriptions explaining project impact");
  
  breakdown.push({
    category: "Projects",
    score: projectsScore,
    maxScore: 15,
    suggestions: projectsSuggestions
  });

  // 6. ATS Compatibility (10 points)
  const atsSuggestions: string[] = [];
  let atsScore = 10;
  
  breakdown.push({
    category: "ATS Compatibility",
    score: atsScore,
    maxScore: 10,
    suggestions: atsSuggestions
  });

  // Calculate overall
  const totalScore = breakdown.reduce((sum, b) => sum + b.score, 0);
  const maxTotal = breakdown.reduce((sum, b) => sum + b.maxScore, 0);
  const overallScore = Math.round((totalScore / maxTotal) * 100);

  let grade: "A" | "B" | "C" | "D" | "F";
  if (overallScore >= 90) grade = "A";
  else if (overallScore >= 80) grade = "B";
  else if (overallScore >= 70) grade = "C";
  else if (overallScore >= 60) grade = "D";
  else grade = "F";

  // Get top 3 suggestions
  const allSuggestions = breakdown.flatMap(b => b.suggestions);
  const topSuggestions = allSuggestions.slice(0, 3);

  return {
    overallScore,
    grade,
    breakdown,
    topSuggestions
  };
}
