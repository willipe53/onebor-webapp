# onebor Web App

The asset allocators toolkit - A React + TypeScript + Vite application with AWS Cognito authentication.

## Features

- User authentication with AWS Cognito
- Email confirmation flow for signup
- Forgot password functionality
- Show/hide password toggles
- Responsive Material-UI design
- onebor logo integration

## Tech Stack

- React 18 with TypeScript
- Vite for build tooling
- Material-UI for components
- AWS Cognito for authentication
- ESLint for code quality

## Getting Started

1. Install dependencies:

   ```bash
   npm install
   ```

2. Start the development server:

   ```bash
   npm run dev
   ```

3. Open [http://localhost:5173](http://localhost:5173) in your browser

## Transaction Processing Workflow

### Simplified Workflow

#### 1. UI Layer

```
TransactionForm → apiService.updateTransaction() → /update_transaction endpoint
```

**That's it!** The UI has zero knowledge of position keepers, locks, or SQS.

#### 2. updatePandaTransaction Lambda

```
Receives transaction data
    ↓
Saves to database (QUEUED status)
    ↓
Sends message to SQS
    ↓
invoke_position_keeper() → calls positionKeeper Lambda asynchronously
```

#### 3. positionKeeper Lambda

```
Receives invocation
    ↓
acquire_distributed_lock() → calls updateLambdaLocks Lambda
    ↓
Lock acquired? → YES: Continue processing SQS messages
                → NO: Exit immediately (another instance is running)
    ↓
Process messages until idle timeout
    ↓
release_distributed_lock() → calls updateLambdaLocks Lambda again
```

### Key Insight

The **UI is completely decoupled** from the processing logic. The UI just says "here's a transaction to process" and the backend handles everything else:

- **Distributed locking** ✅
- **SQS message queuing** ✅
- **Position keeper orchestration** ✅
- **Message processing** ✅
- **Status updates** ✅

The UI doesn't need to know or care about any of this complexity. It's a clean separation of concerns where:

- **Frontend** = User interaction and data presentation
- **Backend** = Business logic, queuing, and processing orchestration
