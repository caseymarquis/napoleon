/**
 * Overview Page Contract
 *
 * The overview shows all projects at a glance: capacity timeline,
 * next-up per project, readiness scores, and collapsible project details.
 */

export type TaskStatus = 'not_started' | 'in_progress' | 'completed' | 'blocked';
export type RiskLevel = 'low' | 'medium' | 'high';

export interface Task {
	id: string;
	title: string;
	description: string;
	status: TaskStatus;
	risk: RiskLevel;
	blockedBy: string[];
	est50: number | null;
	est90: number | null;
	atomic: boolean;
}

export interface ExternalDep {
	description: string;
	resolved: boolean;
	resolvedDate: string | null;
}

export interface Project {
	id: string;
	title: string;
	description: string;
	committedTo: string;
	deadline: string;
	priority: number;
	minimumDelivery: string | null;
	status: string;
	constraints: string[];
	unknowns: string[];
	externalDeps: ExternalDep[];
	tasks: Task[];
}

export interface Repo {
	hash: string;
	name: string;
	url: string;
}

export interface OverviewPageContract {
	/** All projects for the current repo, sorted by priority */
	projects: Project[];

	/** All known repos */
	repos: Repo[];

	/** Currently selected repo hash */
	activeRepo: string;

	/** Whether data is loading */
	loading: boolean;

	/** Switch to a different repo */
	selectRepo(hash: string): void;

	/** Refresh project data */
	refresh(): void;

	/** Update a task's fields */
	updateTask(projectId: string, taskId: string, updates: Partial<Task>): void;
}
