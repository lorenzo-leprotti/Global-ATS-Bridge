import PDFDocument from "pdfkit";
import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle } from "docx";
import type { ParsedResume } from "@shared/schema";

export async function generatePDF(resume: ParsedResume): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    const doc = new PDFDocument({
      size: "LETTER",
      margins: { top: 50, bottom: 50, left: 60, right: 60 }
    });

    doc.on("data", (chunk) => chunks.push(chunk));
    doc.on("end", () => resolve(Buffer.concat(chunks)));
    doc.on("error", reject);

    const colors = {
      primary: "#000000",
      secondary: "#333333",
      muted: "#666666"
    };

    doc.font("Helvetica-Bold")
      .fontSize(18)
      .fillColor(colors.primary)
      .text(resume.personal_info.name.toUpperCase(), { align: "center" });

    doc.moveDown(0.3);

    const contactParts: string[] = [];
    if (resume.personal_info.email) contactParts.push(resume.personal_info.email);
    if (resume.personal_info.phone) contactParts.push(resume.personal_info.phone);
    if (resume.personal_info.location) contactParts.push(resume.personal_info.location);
    if (resume.personal_info.linkedin) contactParts.push(resume.personal_info.linkedin);

    doc.font("Helvetica")
      .fontSize(10)
      .fillColor(colors.secondary)
      .text(contactParts.join(" | "), { align: "center" });

    doc.moveDown(0.3);
    doc.font("Helvetica-Bold")
      .fontSize(10)
      .fillColor(colors.primary)
      .text(resume.personal_info.work_authorization, { align: "center" });

    const addSectionHeader = (title: string) => {
      doc.moveDown(0.8);
      doc.font("Helvetica-Bold")
        .fontSize(12)
        .fillColor(colors.primary)
        .text(title.toUpperCase());
      doc.moveTo(doc.x, doc.y + 2)
        .lineTo(doc.page.width - doc.page.margins.right, doc.y + 2)
        .stroke(colors.primary);
      doc.moveDown(0.4);
    };

    if (resume.education && resume.education.length > 0) {
      addSectionHeader("Education");
      
      for (const edu of resume.education) {
        doc.font("Helvetica-Bold")
          .fontSize(11)
          .fillColor(colors.primary)
          .text(edu.institution, { continued: true });
        
        doc.font("Helvetica")
          .fontSize(10)
          .fillColor(colors.muted)
          .text(`  ${edu.location || ""}`, { align: "right" });

        doc.font("Helvetica")
          .fontSize(10)
          .fillColor(colors.secondary)
          .text(`${edu.degree} in ${edu.field}`, { continued: true });
        
        doc.text(`  ${edu.dates || ""}`, { align: "right" });

        if (edu.gpa) {
          doc.font("Helvetica")
            .fontSize(10)
            .fillColor(colors.muted)
            .text(edu.gpa);
        }

        if (edu.honors) {
          doc.font("Helvetica-Oblique")
            .fontSize(10)
            .fillColor(colors.muted)
            .text(edu.honors);
        }

        doc.moveDown(0.3);
      }
    }

    if (resume.experience && resume.experience.length > 0) {
      addSectionHeader("Experience");
      
      for (const exp of resume.experience) {
        doc.font("Helvetica-Bold")
          .fontSize(11)
          .fillColor(colors.primary)
          .text(exp.title, { continued: true });
        
        doc.font("Helvetica")
          .fontSize(10)
          .fillColor(colors.muted)
          .text(`  ${exp.dates || ""}`, { align: "right" });

        doc.font("Helvetica")
          .fontSize(10)
          .fillColor(colors.secondary)
          .text(`${exp.company}`, { continued: true });
        
        doc.text(`  ${exp.location || ""}`, { align: "right" });

        doc.moveDown(0.2);

        for (const bullet of exp.bullets) {
          doc.font("Helvetica")
            .fontSize(10)
            .fillColor(colors.secondary)
            .text(`• ${bullet}`, { indent: 10 });
        }

        doc.moveDown(0.3);
      }
    }

    if (resume.skills) {
      addSectionHeader("Skills");
      
      if (resume.skills.technical && resume.skills.technical.length > 0) {
        doc.font("Helvetica-Bold")
          .fontSize(10)
          .fillColor(colors.secondary)
          .text("Technical: ", { continued: true });
        doc.font("Helvetica")
          .text(resume.skills.technical.join(", "));
      }

      if (resume.skills.languages && resume.skills.languages.length > 0) {
        doc.font("Helvetica-Bold")
          .fontSize(10)
          .fillColor(colors.secondary)
          .text("Languages: ", { continued: true });
        doc.font("Helvetica")
          .text(resume.skills.languages.join(", "));
      }

      if (resume.skills.certifications && resume.skills.certifications.length > 0) {
        doc.font("Helvetica-Bold")
          .fontSize(10)
          .fillColor(colors.secondary)
          .text("Certifications: ", { continued: true });
        doc.font("Helvetica")
          .text(resume.skills.certifications.join(", "));
      }
    }

    if (resume.projects && resume.projects.length > 0) {
      addSectionHeader("Projects");
      
      for (const project of resume.projects) {
        doc.font("Helvetica-Bold")
          .fontSize(10)
          .fillColor(colors.primary)
          .text(project.name, { continued: true });
        
        if (project.date) {
          doc.font("Helvetica")
            .fontSize(10)
            .fillColor(colors.muted)
            .text(`  ${project.date}`, { align: "right" });
        } else {
          doc.text("");
        }

        doc.font("Helvetica")
          .fontSize(10)
          .fillColor(colors.secondary)
          .text(project.description);

        if (project.technologies.length > 0) {
          doc.font("Helvetica-Oblique")
            .fontSize(9)
            .fillColor(colors.muted)
            .text(`Technologies: ${project.technologies.join(", ")}`);
        }

        doc.moveDown(0.3);
      }
    }

    doc.end();
  });
}

export async function generateDOCX(resume: ParsedResume): Promise<Buffer> {
  const sections: Paragraph[] = [];

  sections.push(
    new Paragraph({
      children: [
        new TextRun({
          text: resume.personal_info.name.toUpperCase(),
          bold: true,
          size: 32
        })
      ],
      alignment: AlignmentType.CENTER,
      spacing: { after: 100 }
    })
  );

  const contactParts: string[] = [];
  if (resume.personal_info.email) contactParts.push(resume.personal_info.email);
  if (resume.personal_info.phone) contactParts.push(resume.personal_info.phone);
  if (resume.personal_info.location) contactParts.push(resume.personal_info.location);
  if (resume.personal_info.linkedin) contactParts.push(resume.personal_info.linkedin);

  sections.push(
    new Paragraph({
      children: [
        new TextRun({
          text: contactParts.join(" | "),
          size: 20
        })
      ],
      alignment: AlignmentType.CENTER,
      spacing: { after: 100 }
    })
  );

  sections.push(
    new Paragraph({
      children: [
        new TextRun({
          text: resume.personal_info.work_authorization,
          bold: true,
          size: 20
        })
      ],
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 }
    })
  );

  const addSectionHeader = (title: string) => {
    sections.push(
      new Paragraph({
        children: [
          new TextRun({
            text: title.toUpperCase(),
            bold: true,
            size: 24
          })
        ],
        border: {
          bottom: { style: BorderStyle.SINGLE, size: 6, color: "000000" }
        },
        spacing: { before: 200, after: 100 }
      })
    );
  };

  if (resume.education && resume.education.length > 0) {
    addSectionHeader("Education");
    
    for (const edu of resume.education) {
      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: edu.institution, bold: true, size: 22 }),
            new TextRun({ text: `  |  ${edu.location || ""}`, size: 20 })
          ],
          spacing: { after: 50 }
        })
      );

      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: `${edu.degree} in ${edu.field}`, size: 20 }),
            new TextRun({ text: `  |  ${edu.dates || ""}`, size: 20 })
          ],
          spacing: { after: 50 }
        })
      );

      if (edu.gpa) {
        sections.push(
          new Paragraph({
            children: [new TextRun({ text: edu.gpa, size: 20, color: "666666" })],
            spacing: { after: 50 }
          })
        );
      }

      if (edu.honors) {
        sections.push(
          new Paragraph({
            children: [new TextRun({ text: edu.honors, italics: true, size: 20 })],
            spacing: { after: 100 }
          })
        );
      }
    }
  }

  if (resume.experience && resume.experience.length > 0) {
    addSectionHeader("Experience");
    
    for (const exp of resume.experience) {
      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: exp.title, bold: true, size: 22 }),
            new TextRun({ text: `  |  ${exp.dates || ""}`, size: 20 })
          ],
          spacing: { after: 50 }
        })
      );

      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: exp.company, size: 20 }),
            new TextRun({ text: `  |  ${exp.location || ""}`, size: 20 })
          ],
          spacing: { after: 50 }
        })
      );

      for (const bullet of exp.bullets) {
        sections.push(
          new Paragraph({
            children: [new TextRun({ text: `• ${bullet}`, size: 20 })],
            indent: { left: 360 },
            spacing: { after: 50 }
          })
        );
      }
    }
  }

  if (resume.skills) {
    addSectionHeader("Skills");
    
    if (resume.skills.technical && resume.skills.technical.length > 0) {
      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: "Technical: ", bold: true, size: 20 }),
            new TextRun({ text: resume.skills.technical.join(", "), size: 20 })
          ],
          spacing: { after: 50 }
        })
      );
    }

    if (resume.skills.languages && resume.skills.languages.length > 0) {
      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: "Languages: ", bold: true, size: 20 }),
            new TextRun({ text: resume.skills.languages.join(", "), size: 20 })
          ],
          spacing: { after: 50 }
        })
      );
    }

    if (resume.skills.certifications && resume.skills.certifications.length > 0) {
      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: "Certifications: ", bold: true, size: 20 }),
            new TextRun({ text: resume.skills.certifications.join(", "), size: 20 })
          ],
          spacing: { after: 50 }
        })
      );
    }
  }

  if (resume.projects && resume.projects.length > 0) {
    addSectionHeader("Projects");
    
    for (const project of resume.projects) {
      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: project.name, bold: true, size: 20 }),
            project.date ? new TextRun({ text: `  |  ${project.date}`, size: 20 }) : new TextRun({ text: "" })
          ],
          spacing: { after: 50 }
        })
      );

      sections.push(
        new Paragraph({
          children: [new TextRun({ text: project.description, size: 20 })],
          spacing: { after: 50 }
        })
      );

      if (project.technologies.length > 0) {
        sections.push(
          new Paragraph({
            children: [
              new TextRun({ text: `Technologies: ${project.technologies.join(", ")}`, italics: true, size: 18, color: "666666" })
            ],
            spacing: { after: 100 }
          })
        );
      }
    }
  }

  const doc = new Document({
    sections: [{
      properties: {},
      children: sections
    }]
  });

  return await Packer.toBuffer(doc);
}
