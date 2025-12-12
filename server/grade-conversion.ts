interface GradeConversion {
  pattern: RegExp;
  convert: (match: RegExpMatchArray) => string;
}

const gradeConversions: GradeConversion[] = [
  {
    pattern: /110\s*(?:e\s*)?[Ll]ode\s*\/?\s*110|110L\s*\/?\s*110/i,
    convert: () => "GPA: 4.0/4.0 (Italian: 110 e Lode/110)"
  },
  {
    pattern: /30\s*(?:e\s*)?[Ll]ode\s*\/?\s*30|30L\s*\/?\s*30/i,
    convert: () => "GPA: 4.0/4.0 (Italian: 30 e Lode/30)"
  },
  {
    pattern: /(\d{2,3})\s*\/\s*110/i,
    convert: (match) => {
      const score = parseInt(match[1]);
      if (score >= 105) return `GPA: 3.9-4.0/4.0 (Italian: ${score}/110)`;
      if (score >= 100) return `GPA: 3.7-3.9/4.0 (Italian: ${score}/110)`;
      if (score >= 90) return `GPA: 3.0-3.5/4.0 (Italian: ${score}/110)`;
      return `GPA: 2.5-3.0/4.0 (Italian: ${score}/110)`;
    }
  },
  {
    pattern: /(\d{1,2})\s*\/\s*30/i,
    convert: (match) => {
      const score = parseInt(match[1]);
      if (score === 30) return `GPA: 3.9-4.0/4.0 (Italian: ${score}/30)`;
      if (score >= 27) return `GPA: 3.7-3.9/4.0 (Italian: ${score}/30)`;
      if (score >= 24) return `GPA: 3.0-3.5/4.0 (Italian: ${score}/30)`;
      return `GPA: 2.5-3.0/4.0 (Italian: ${score}/30)`;
    }
  },
  {
    pattern: /[Ff]irst[- ]?[Cc]lass\s*[Hh]onours?/i,
    convert: () => "GPA: 3.7-4.0/4.0 (UK: First-Class Honours)"
  },
  {
    pattern: /[Uu]pper\s*[Ss]econd(?:\s*[Cc]lass)?|2[:\.]?1|2:1/i,
    convert: () => "GPA: 3.3-3.7/4.0 (UK: Upper Second Class - 2:1)"
  },
  {
    pattern: /[Ll]ower\s*[Ss]econd(?:\s*[Cc]lass)?|2[:\.]?2|2:2/i,
    convert: () => "GPA: 3.0-3.3/4.0 (UK: Lower Second Class - 2:2)"
  },
  {
    pattern: /[Ss]ehr\s*[Gg]ut|1[.,][0-5]/i,
    convert: (match) => {
      const text = match[0];
      if (/1[.,][0-2]/.test(text)) return "GPA: 3.9-4.0/4.0 (German: Sehr Gut)";
      return "GPA: 3.8-4.0/4.0 (German: Sehr Gut)";
    }
  },
  {
    pattern: /[Gg]ut|1[.,][6-9]|2[.,][0-5]/i,
    convert: () => "GPA: 3.0-3.7/4.0 (German: Gut)"
  },
  {
    pattern: /[Ff]irst\s*[Dd]ivision|\b(60|[6-9]\d|100)\s*%/i,
    convert: (match) => {
      const text = match[0];
      const percentMatch = text.match(/(\d+)\s*%/);
      if (percentMatch) {
        const percent = parseInt(percentMatch[1]);
        if (percent >= 75) return `GPA: 3.7-4.0/4.0 (Indian: ${percent}%)`;
        if (percent >= 60) return `GPA: 3.5-4.0/4.0 (Indian: ${percent}%)`;
      }
      return "GPA: 3.5-4.0/4.0 (Indian: First Division)";
    }
  },
  {
    pattern: /[Ss]econd\s*[Dd]ivision|\b(50|5\d)\s*%/i,
    convert: (match) => {
      const text = match[0];
      const percentMatch = text.match(/(\d+)\s*%/);
      if (percentMatch) {
        return `GPA: 2.5-3.0/4.0 (Indian: ${percentMatch[1]}%)`;
      }
      return "GPA: 2.5-3.0/4.0 (Indian: Second Division)";
    }
  },
  {
    pattern: /CGPA[:\s]*(\d+(?:\.\d+)?)\s*\/?\s*10/i,
    convert: (match) => {
      const cgpa = parseFloat(match[1]);
      const gpa = (cgpa / 10 * 4).toFixed(1);
      return `GPA: ${gpa}/4.0 (Indian CGPA: ${cgpa}/10)`;
    }
  }
];

export function convertGrade(gradeText: string): { converted: string; wasConverted: boolean } {
  for (const conversion of gradeConversions) {
    const match = gradeText.match(conversion.pattern);
    if (match) {
      return {
        converted: conversion.convert(match),
        wasConverted: true
      };
    }
  }
  return { converted: gradeText, wasConverted: false };
}

export function detectAndConvertGrades(text: string): {
  convertedText: string;
  conversions: Array<{ original: string; converted: string }>;
} {
  const conversions: Array<{ original: string; converted: string }> = [];
  let convertedText = text;

  for (const conversion of gradeConversions) {
    const match = text.match(conversion.pattern);
    if (match) {
      const original = match[0];
      const converted = conversion.convert(match);
      conversions.push({ original, converted });
      convertedText = convertedText.replace(original, converted);
    }
  }

  return { convertedText, conversions };
}
