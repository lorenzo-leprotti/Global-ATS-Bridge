import { randomUUID } from "crypto";
import type { ProcessingSession, ParsedResume, DetectedIssue, AppliedChange } from "@shared/schema";

interface SessionData {
  session: ProcessingSession;
  parsedResume?: ParsedResume;
  originalText?: string;
  detectedIssues?: DetectedIssue[];
  appliedChanges?: AppliedChange[];
  workAuthorization: string;
  outputFormat: "pdf" | "docx";
}

export interface IStorage {
  createSession(workAuthorization: string, outputFormat: "pdf" | "docx"): ProcessingSession;
  getSession(id: string): SessionData | undefined;
  updateSession(id: string, data: Partial<SessionData>): void;
  deleteSession(id: string): void;
  cleanExpiredSessions(): void;
}

export class MemStorage implements IStorage {
  private sessions: Map<string, SessionData>;
  private cleanupInterval: NodeJS.Timeout;

  constructor() {
    this.sessions = new Map();
    this.cleanupInterval = setInterval(() => this.cleanExpiredSessions(), 60000);
    
    process.on('SIGTERM', () => this.shutdown());
    process.on('SIGINT', () => this.shutdown());
  }

  private shutdown(): void {
    console.log('Shutting down: clearing all session data for privacy...');
    clearInterval(this.cleanupInterval);
    this.sessions.clear();
    console.log('All session data purged.');
    process.exit(0);
  }

  getActiveSessionCount(): number {
    return this.sessions.size;
  }

  createSession(workAuthorization: string, outputFormat: "pdf" | "docx"): ProcessingSession {
    const id = randomUUID();
    const now = new Date();
    const expiresAt = new Date(now.getTime() + 15 * 60 * 1000);

    const session: ProcessingSession = {
      id,
      uploadedAt: now.toISOString(),
      expiresAt: expiresAt.toISOString()
    };

    this.sessions.set(id, {
      session,
      workAuthorization,
      outputFormat
    });

    return session;
  }

  getSession(id: string): SessionData | undefined {
    const data = this.sessions.get(id);
    if (!data) return undefined;

    if (new Date(data.session.expiresAt) < new Date()) {
      this.sessions.delete(id);
      return undefined;
    }

    return data;
  }

  updateSession(id: string, data: Partial<SessionData>): void {
    const existing = this.sessions.get(id);
    if (existing) {
      this.sessions.set(id, { ...existing, ...data });
    }
  }

  deleteSession(id: string): void {
    this.sessions.delete(id);
  }

  cleanExpiredSessions(): void {
    const now = new Date();
    const entries = Array.from(this.sessions.entries());
    for (const [id, data] of entries) {
      if (new Date(data.session.expiresAt) < now) {
        this.sessions.delete(id);
      }
    }
  }
}

export const storage = new MemStorage();
