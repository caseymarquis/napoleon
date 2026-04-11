# Contract UI Architecture

## Why This Exists

Traditional frontend development couples the UI to the backend from day one. Every UX iteration requires a round trip through the API layer before you can see if the interaction feels right.

**AI-assisted development changes the equation.** An AI can generate test data, stub implementations, and build out complete UI workflows in seconds. The bottleneck is no longer writing code — it's the cycle of discovering what the UX should actually be. This architecture eliminates that cost during the discovery phase.

We build the entire UX in isolation, driven by what the user needs to see and do. Then we wire the backend. We're no longer changing several systems simultaneously just to find out the UX is wrong.

## Three Roles

| Role | Suffix | Location | Description |
|------|--------|----------|-------------|
| **Contract** | `*PageContract.ts` | `src/pages/{name}/` | Pure TypeScript interface + DTOs. Zero external imports. |
| **Page** | `*Page.svelte` | `src/pages/{name}/` | The UI component. Accepts a single contract prop. Owns the UX. |
| **Host** | `*Host.svelte` | `src/routes/` (or parent) | The adapter. Implements the contract, wires to the API. |

The **Page** is what the user sees. The **Host** is plumbing that connects the Page to the real world. The **Contract** is the boundary between them.

Sub-components within a page are named for what they render — `CapacityTimeline.svelte`, `ProjectCard.svelte`, `ReadinessPanel.svelte`. They can have their own contracts if complex enough, or accept props from the parent Page's contract types.

## How It Works

### The Contract

Every page defines a contract — a plain TypeScript interface that describes everything the Page needs from the outside world. The contract has zero imports from API clients, fetch calls, or backend types.

```typescript
// src/pages/overview/OverviewPageContract.ts

export interface Project {
  id: string;
  title: string;
  deadline: string;
  tasks: Task[];
  // ... shaped for the UI, not the database
}

export interface OverviewPageContract {
  projects: Project[];
  loading: boolean;
  activeRepo: string;

  selectRepo(hash: string): void;
  refresh(): void;
}
```

The contract defines:

- **Display types** — what the Page needs to render. Shaped for the UI, not the backend.
- **Methods** — actions the Page can invoke, expressed as intent.
- **State** — reactive data the Page reads.

### The Page

The Page accepts a single prop: the contract. It imports nothing from fetch, no API URLs, no backend types. It knows only about:

- Svelte (framework)
- The contract (its own types)
- Shared UI components from `src/shared-components/`

```svelte
<script lang="ts">
  import type { OverviewPageContract } from './OverviewPageContract';

  let { contract }: { contract: OverviewPageContract } = $props();

  // All data comes from contract.projects, contract.loading, etc.
  // All actions go through contract.selectRepo(), contract.refresh(), etc.
</script>
```

### The Host

The Host creates a `$state` implementation of the contract. This is where the outside world connects:

- API calls translate between contract types and backend responses
- Polling, WebSocket events update contract state
- Backend-specific logic lives here

```svelte
<!-- src/routes/+page.svelte -->
<script lang="ts">
  import OverviewPage from '../pages/overview/OverviewPage.svelte';
  import type { OverviewPageContract, Project } from '../pages/overview/OverviewPageContract';

  let contract: OverviewPageContract = $state({
    projects: [],
    loading: true,
    activeRepo: '',

    async selectRepo(hash: string) {
      contract.activeRepo = hash;
      await contract.refresh();
    },

    async refresh() {
      contract.loading = true;
      const res = await fetch(`/api/projects?p=${contract.activeRepo}`);
      contract.projects = await res.json();
      contract.loading = false;
    }
  });
</script>

<OverviewPage {contract} />
```

The Host is the thinnest possible adapter. It should be boring — mostly fetching and mapping.

### Tests

Tests create a contract with stub data. No backend running, no API calls.

```typescript
import { render, screen } from '@testing-library/svelte';
import OverviewPage from './OverviewPage.svelte';
import type { OverviewPageContract } from './OverviewPageContract';

function makeContract(overrides: Partial<OverviewPageContract> = {}): OverviewPageContract {
  return {
    projects: [],
    loading: false,
    activeRepo: 'abc123',
    repos: [],
    selectRepo: vi.fn(),
    refresh: vi.fn(),
    ...overrides,
  };
}

test('shows project count', () => {
  const contract = makeContract({
    projects: [
      { id: 'test', title: 'Test Project', /* ... */ },
    ],
  });

  render(OverviewPage, { props: { contract } });
  expect(screen.getByText('Test Project')).toBeInTheDocument();
});
```

### WIP vs Stable Tests

During UX exploration, keep all tests in a `.wip.test.ts` file. Don't maintain stable tests while the contract shape is actively changing.

The workflow:
1. **One active test** in `PageName.wip.test.ts` — a single user story driving the UI
2. **Graduate** once the story is solid — move it into `PageName.test.ts`
3. **Start the next story** in the WIP file
4. **Delete the WIP file** when all stories are graduated

## Guiding Principles

**The contract is the source of truth for what the UI needs.** If the Page needs a new field, add it to the contract. The backend adapts to serve it.

**The contract carries semantic data, not display data.** Status fields are enums or well-defined values — the Page decides how to display them (colors, icons, labels).

**Commands express intent, not mechanics.** `markDone(taskIndex)` — not "PATCH this JSON field."

**The Host is the translation layer.** Thinnest possible adapter between the contract's world and the API.

**The contract must be reactive.** The Host creates it with Svelte's `$state`. The Page reads from it. When the Host mutates state, the Page re-renders automatically.

## When to Use This Pattern

Always.
