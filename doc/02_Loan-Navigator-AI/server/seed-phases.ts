import { drizzle } from "drizzle-orm/node-postgres";
import pg from "pg";
import { loanPhases } from "@shared/schema";

const DEFAULT_PHASES = [
  { name: "Lead & Inquiry", description: "Initial contact and inquiry from the borrower", sortOrder: 1, color: "#60a5fa", icon: "user-plus" },
  { name: "Application Submission", description: "Formal loan application submitted by the borrower", sortOrder: 2, color: "#34d399", icon: "file-text" },
  { name: "Document Collection & KYC", description: "Gathering required documents and completing KYC verification", sortOrder: 3, color: "#fbbf24", icon: "folder-open" },
  { name: "Verification & Credit Appraisal", description: "Background verification and credit score appraisal", sortOrder: 4, color: "#f97316", icon: "search" },
  { name: "Underwriting & Credit Decision", description: "Risk assessment and credit decision by the underwriting team", sortOrder: 5, color: "#a78bfa", icon: "shield-check" },
  { name: "Conditional Approval & Offer", description: "Conditional approval issued with loan terms and offer letter", sortOrder: 6, color: "#2dd4bf", icon: "check-circle" },
  { name: "Security & Legal Documentation", description: "Legal documentation, mortgage registration, and security creation", sortOrder: 7, color: "#ec4899", icon: "scale" },
  { name: "Pre-Disbursement Checks", description: "Final checks before funds are disbursed", sortOrder: 8, color: "#14b8a6", icon: "clipboard-check" },
  { name: "Disbursement", description: "Loan amount disbursed to the borrower's account", sortOrder: 9, color: "#22c55e", icon: "banknote" },
];

async function seedPhases() {
  const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
  const db = drizzle(pool);

  const existing = await db.select().from(loanPhases);
  if (existing.length > 0) {
    console.log(`Phases already seeded (${existing.length} found). Skipping.`);
    await pool.end();
    return;
  }

  for (const phase of DEFAULT_PHASES) {
    await db.insert(loanPhases).values(phase);
  }

  console.log(`Seeded ${DEFAULT_PHASES.length} default loan phases.`);
  await pool.end();
}

seedPhases().catch(console.error);
