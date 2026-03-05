# User Guide: ML Model Training Workflow

## Overview
This guide explains how to use the new Admin Panel ML Model Training interface to manage the credit risk model lifecycle.

### Prerequisites
- You must have an **Admin** or **Operator** account.
- Backend services must be running and connected to MLflow.

### 1. Accessing the Training Panel
1. Log in to the application.
2. In the left sidebar, click **ML Training**.
3. You will see the Training Pipeline dashboard with three main steps:
   - **Planning**: Define the training strategy.
   - **Execution**: Run the training job.
   - **Deployment**: Review results and deploy the model.

### 2. Step 1: Planning
1. Enter a **Rationale** for this training run (e.g., "Quarterly refresh with new data").
2. Click **Generate Plan**.
3. Wait for the backend to propose hyperparameters and data sample size.
4. Review the generated plan in the JSON viewer.

### 3. Step 2: Execution
1. Once the plan is generated, click **Execute Training**.
2. The button will change to "Training..." while the job runs.
3. Upon completion, you will see a success message with training metrics (Accuracy, AUC).
   - If training fails, check the backend logs or try adjusting the plan.

### 4. Step 3: Deployment & Validation
1. **Review Results**: Check the training metrics (Accuracy > 0.90 is recommended).
2. **Run Drift Check**: Click **Run Drift Check** to analyze data drift between training and production data.
   - View the generated HTML report by clicking **View Report**.
3. **Deploy Model**:
   - If satisfied with the results, click **Deploy Model**.
   - This triggers a hot-reload of the inference service.
   - A success alert will confirm the model is live.

### Troubleshooting
- **"Failed to load MLflow model"**: Ensure the MLflow server is running and accessible. Check network connectivity.
- **"Plan generation failed"**: The backend AI agent may be unavailable. Retry or check logs.
- **Drift Report not opening**: Ensure pop-ups are allowed for the site.
