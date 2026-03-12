import {
  type User, type InsertUser,
  type Conversation, type InsertConversation,
  type Message, type InsertMessage,
  type LoanPhase, type InsertLoanPhase,
  type Loan, type InsertLoan,
  type CatalogProduct, type InsertCatalogProduct,
  users, conversations, messages, loanPhases, loans, loanProductCatalog,
} from "@shared/schema";
import { drizzle } from "drizzle-orm/node-postgres";
import { eq, desc, asc } from "drizzle-orm";
import pg from "pg";

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
});

const db = drizzle(pool);

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  createConversation(data: InsertConversation): Promise<Conversation>;
  getConversation(id: string): Promise<Conversation | undefined>;
  getAllConversations(): Promise<Conversation[]>;
  updateConversation(id: string, data: Partial<InsertConversation>): Promise<Conversation>;

  createMessage(data: InsertMessage): Promise<Message>;
  getMessagesByConversation(conversationId: string): Promise<Message[]>;

  getActivePhases(): Promise<LoanPhase[]>;
  getAllPhases(): Promise<LoanPhase[]>;
  getPhase(id: string): Promise<LoanPhase | undefined>;
  getPhaseByName(name: string): Promise<LoanPhase | undefined>;
  createPhase(data: InsertLoanPhase): Promise<LoanPhase>;
  updatePhase(id: string, data: Partial<InsertLoanPhase>): Promise<LoanPhase>;
  deactivatePhase(id: string): Promise<LoanPhase>;
  reorderPhases(phaseIds: string[]): Promise<LoanPhase[]>;
  getMaxSortOrder(): Promise<number>;

  createLoan(data: InsertLoan): Promise<Loan>;
  getLoan(id: string): Promise<Loan | undefined>;
  getAllLoans(): Promise<Loan[]>;
  updateLoan(id: string, data: Partial<InsertLoan>): Promise<Loan>;

  createCatalogProduct(data: InsertCatalogProduct): Promise<CatalogProduct>;
  getCatalogProduct(id: string): Promise<CatalogProduct | undefined>;
  getAllCatalogProducts(): Promise<CatalogProduct[]>;
  updateCatalogProduct(id: string, data: Partial<InsertCatalogProduct>): Promise<CatalogProduct>;
  deleteCatalogProduct(id: string): Promise<void>;
}

export class DatabaseStorage implements IStorage {
  async getUser(id: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db.insert(users).values(insertUser).returning();
    return user;
  }

  async createConversation(data: InsertConversation): Promise<Conversation> {
    const [conversation] = await db.insert(conversations).values(data).returning();
    return conversation;
  }

  async getConversation(id: string): Promise<Conversation | undefined> {
    const [conversation] = await db.select().from(conversations).where(eq(conversations.id, id));
    return conversation;
  }

  async getAllConversations(): Promise<Conversation[]> {
    return db.select().from(conversations).orderBy(desc(conversations.createdAt));
  }

  async updateConversation(id: string, data: Partial<InsertConversation>): Promise<Conversation> {
    const [conversation] = await db.update(conversations).set(data).where(eq(conversations.id, id)).returning();
    return conversation;
  }

  async createMessage(data: InsertMessage): Promise<Message> {
    const [message] = await db.insert(messages).values(data).returning();
    return message;
  }

  async getMessagesByConversation(conversationId: string): Promise<Message[]> {
    return db.select().from(messages).where(eq(messages.conversationId, conversationId)).orderBy(messages.createdAt);
  }

  async getActivePhases(): Promise<LoanPhase[]> {
    return db.select().from(loanPhases).where(eq(loanPhases.isActive, true)).orderBy(asc(loanPhases.sortOrder));
  }

  async getAllPhases(): Promise<LoanPhase[]> {
    return db.select().from(loanPhases).orderBy(asc(loanPhases.sortOrder));
  }

  async getPhase(id: string): Promise<LoanPhase | undefined> {
    const [phase] = await db.select().from(loanPhases).where(eq(loanPhases.id, id));
    return phase;
  }

  async getPhaseByName(name: string): Promise<LoanPhase | undefined> {
    const allPhases = await this.getAllPhases();
    return allPhases.find(p => p.name.toLowerCase() === name.toLowerCase());
  }

  async createPhase(data: InsertLoanPhase): Promise<LoanPhase> {
    const [phase] = await db.insert(loanPhases).values(data).returning();
    return phase;
  }

  async updatePhase(id: string, data: Partial<InsertLoanPhase>): Promise<LoanPhase> {
    const [phase] = await db.update(loanPhases).set({ ...data, updatedAt: new Date() }).where(eq(loanPhases.id, id)).returning();
    return phase;
  }

  async deactivatePhase(id: string): Promise<LoanPhase> {
    const [phase] = await db.update(loanPhases).set({ isActive: false, updatedAt: new Date() }).where(eq(loanPhases.id, id)).returning();
    return phase;
  }

  async reorderPhases(phaseIds: string[]): Promise<LoanPhase[]> {
    const results: LoanPhase[] = [];
    for (let i = 0; i < phaseIds.length; i++) {
      const [phase] = await db.update(loanPhases).set({ sortOrder: i + 1, updatedAt: new Date() }).where(eq(loanPhases.id, phaseIds[i])).returning();
      if (phase) results.push(phase);
    }
    return results;
  }

  async getMaxSortOrder(): Promise<number> {
    const phases = await this.getAllPhases();
    if (phases.length === 0) return 0;
    return Math.max(...phases.map(p => p.sortOrder));
  }

  async createLoan(data: InsertLoan): Promise<Loan> {
    const [loan] = await db.insert(loans).values(data).returning();
    return loan;
  }

  async getLoan(id: string): Promise<Loan | undefined> {
    const [loan] = await db.select().from(loans).where(eq(loans.id, id));
    return loan;
  }

  async getAllLoans(): Promise<Loan[]> {
    return db.select().from(loans).orderBy(desc(loans.createdAt));
  }

  async updateLoan(id: string, data: Partial<InsertLoan>): Promise<Loan> {
    const [loan] = await db.update(loans).set({ ...data, updatedAt: new Date() }).where(eq(loans.id, id)).returning();
    return loan;
  }

  async createCatalogProduct(data: InsertCatalogProduct): Promise<CatalogProduct> {
    const [product] = await db.insert(loanProductCatalog).values(data).returning();
    return product;
  }

  async getCatalogProduct(id: string): Promise<CatalogProduct | undefined> {
    const [product] = await db.select().from(loanProductCatalog).where(eq(loanProductCatalog.id, id));
    return product;
  }

  async getAllCatalogProducts(): Promise<CatalogProduct[]> {
    return db.select().from(loanProductCatalog).orderBy(desc(loanProductCatalog.createdAt));
  }

  async updateCatalogProduct(id: string, data: Partial<InsertCatalogProduct>): Promise<CatalogProduct> {
    const [product] = await db.update(loanProductCatalog).set({ ...data, updatedAt: new Date() }).where(eq(loanProductCatalog.id, id)).returning();
    return product;
  }

  async deleteCatalogProduct(id: string): Promise<void> {
    await db.delete(loanProductCatalog).where(eq(loanProductCatalog.id, id));
  }
}

export const storage = new DatabaseStorage();
