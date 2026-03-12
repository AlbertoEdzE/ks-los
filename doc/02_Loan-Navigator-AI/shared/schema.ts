import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, timestamp, jsonb, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const conversations = pgTable("conversations", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  borrowerName: text("borrower_name"),
  status: text("status").notNull().default("active"),
  chatRole: text("chat_role").notNull().default("borrower"),
  currentPhaseId: varchar("current_phase_id"),
  seriousnessScore: integer("seriousness_score"),
  fitScore: integer("fit_score"),
  intentSummary: jsonb("intent_summary"),
  recommendedProducts: jsonb("recommended_products"),
  nextConversationAngle: text("next_conversation_angle"),
  assignedOfficer: varchar("assigned_officer"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const messages = pgTable("messages", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  conversationId: varchar("conversation_id").notNull(),
  role: text("role").notNull(),
  content: text("content").notNull(),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const loanPhases = pgTable("loan_phases", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: text("name").notNull(),
  description: text("description"),
  sortOrder: integer("sort_order").notNull(),
  isActive: boolean("is_active").notNull().default(true),
  color: text("color").default("#2dd4bf"),
  icon: text("icon").default("circle"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const loans = pgTable("loans", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  borrowerName: text("borrower_name").notNull(),
  borrowerEmail: text("borrower_email"),
  borrowerPhone: text("borrower_phone"),
  loanType: text("loan_type").notNull(),
  loanAmount: text("loan_amount").notNull(),
  interestRate: text("interest_rate"),
  tenure: text("tenure"),
  monthlyEmi: text("monthly_emi"),
  purpose: text("purpose"),
  employmentType: text("employment_type"),
  monthlyIncome: text("monthly_income"),
  existingDebts: text("existing_debts"),
  creditScore: text("credit_score"),
  collateral: text("collateral"),
  downPayment: text("down_payment"),
  propertyValue: text("property_value"),
  ltv: text("ltv"),
  currentPhaseId: varchar("current_phase_id"),
  status: text("status").notNull().default("draft"),
  notes: text("notes"),
  conversationId: varchar("conversation_id"),
  createdBy: varchar("created_by"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const loanProductCatalog = pgTable("loan_product_catalog", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: text("name").notNull(),
  code: text("code").notNull().unique(),
  category: text("category").notNull(),
  description: text("description"),
  minAmount: text("min_amount"),
  maxAmount: text("max_amount"),
  minTenureMonths: integer("min_tenure_months"),
  maxTenureMonths: integer("max_tenure_months"),
  baseInterestRate: text("base_interest_rate"),
  maxInterestRate: text("max_interest_rate"),
  processingFeePercent: text("processing_fee_percent"),
  prepaymentPenalty: text("prepayment_penalty"),
  minCreditScore: integer("min_credit_score"),
  maxLtv: text("max_ltv"),
  minIncome: text("min_income"),
  collateralRequired: boolean("collateral_required").default(false),
  requiredDocuments: text("required_documents").array(),
  eligibilityCriteria: text("eligibility_criteria").array(),
  features: text("features").array(),
  targetSegment: text("target_segment"),
  riskGrade: text("risk_grade"),
  insuranceRequired: boolean("insurance_required").default(false),
  status: text("status").notNull().default("draft"),
  icon: text("icon").default("banknote"),
  color: text("color").default("#0d9488"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertLoanProductCatalogSchema = createInsertSchema(loanProductCatalog).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type CatalogProduct = typeof loanProductCatalog.$inferSelect;
export type InsertCatalogProduct = z.infer<typeof insertLoanProductCatalogSchema>;

export const insertLoanSchema = createInsertSchema(loans).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type Loan = typeof loans.$inferSelect;
export type InsertLoan = z.infer<typeof insertLoanSchema>;

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export const insertConversationSchema = createInsertSchema(conversations).omit({
  id: true,
  createdAt: true,
});

export const insertMessageSchema = createInsertSchema(messages).omit({
  id: true,
  createdAt: true,
});

export const insertLoanPhaseSchema = createInsertSchema(loanPhases).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type Conversation = typeof conversations.$inferSelect;
export type InsertConversation = z.infer<typeof insertConversationSchema>;
export type Message = typeof messages.$inferSelect;
export type InsertMessage = z.infer<typeof insertMessageSchema>;
export type LoanPhase = typeof loanPhases.$inferSelect;
export type InsertLoanPhase = z.infer<typeof insertLoanPhaseSchema>;

export const intentSummarySchema = z.object({
  purpose: z.string().optional(),
  urgency: z.enum(["low", "medium", "high", "critical"]).optional(),
  affordability: z.string().optional(),
  monthlyIncome: z.string().optional(),
  existingDebts: z.string().optional(),
  loanAmount: z.string().optional(),
  preferredTenure: z.string().optional(),
  collateralAvailable: z.string().optional(),
  employmentType: z.string().optional(),
  creditHistory: z.string().optional(),
});

export const loanProductSchema = z.object({
  name: z.string(),
  type: z.string(),
  estimatedRate: z.string(),
  estimatedEmi: z.string(),
  tenure: z.string(),
  totalInterest: z.string(),
  approvalSpeed: z.string(),
  pros: z.array(z.string()),
  cons: z.array(z.string()),
  recommendation: z.string(),
});

export type IntentSummary = z.infer<typeof intentSummarySchema>;
export type LoanProduct = z.infer<typeof loanProductSchema>;
