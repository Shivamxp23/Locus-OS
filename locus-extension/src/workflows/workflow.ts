/**
 * Locus Workflow Engine (§29.8) TypeScript companion.
 */

export enum StepStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  SUCCESS = 'success',
  FAILED = 'failed',
  SKIPPED = 'skipped',
}

export interface WorkflowStep {
  stepId: string;
  actionName: string;
  dependsOn?: string[];
  params?: Record<string, any>;
  maxRetries?: number;
  status?: StepStatus;
  result?: any;
  error?: string;
}

export interface WorkflowExecutionResult {
  workflowId: string;
  success: boolean;
  stepResults: Record<string, any>;
  durationSeconds: number;
  failedStep?: string;
}

export class WorkflowEngine {
  private actionRegistry: Map<string, (params: Record<string, any>, ctx: Record<string, any>) => any> = new Map();

  registerAction(name: string, fn: (params: Record<string, any>, ctx: Record<string, any>) => any): void {
    this.actionRegistry.set(name, fn);
  }

  async executeWorkflow(workflowId: string, steps: WorkflowStep[]): Promise<WorkflowExecutionResult> {
    const startTime = Date.now();
    const context: Record<string, any> = {};
    const completedSteps = new Set<string>();

    while (completedSteps.size < steps.length) {
      const readySteps = steps.filter(
        (s) => !completedSteps.has(s.stepId) && (s.dependsOn || []).every((d) => completedSteps.has(d))
      );

      if (readySteps.length === 0) {
        return {
          workflowId,
          success: false,
          stepResults: context,
          durationSeconds: (Date.now() - startTime) / 1000,
          failedStep: 'UNSATISFIED_DEPENDENCIES',
        };
      }

      for (const step of readySteps) {
        const fn = this.actionRegistry.get(step.actionName);
        if (!fn) {
          step.status = StepStatus.FAILED;
          step.error = `Action '${step.actionName}' not registered`;
          return {
            workflowId,
            success: false,
            stepResults: context,
            durationSeconds: (Date.now() - startTime) / 1000,
            failedStep: step.stepId,
          };
        }

        step.status = StepStatus.RUNNING;
        let success = false;
        let lastErr = '';
        const maxRetries = step.maxRetries ?? 1;

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
          try {
            const res = await Promise.resolve(fn(step.params || {}, context));
            step.status = StepStatus.SUCCESS;
            step.result = res;
            context[step.stepId] = res;
            success = true;
            break;
          } catch (err: any) {
            lastErr = err?.message || String(err);
          }
        }

        if (!success) {
          step.status = StepStatus.FAILED;
          step.error = lastErr;
          return {
            workflowId,
            success: false,
            stepResults: context,
            durationSeconds: (Date.now() - startTime) / 1000,
            failedStep: step.stepId,
          };
        }

        completedSteps.add(step.stepId);
      }
    }

    return {
      workflowId,
      success: true,
      stepResults: context,
      durationSeconds: (Date.now() - startTime) / 1000,
    };
  }
}
