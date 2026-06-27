import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="p-8 text-center text-text-muted text-sm">
            Algo deu errado.{" "}
            <button onClick={() => this.setState({ hasError: false })} className="text-primary hover:underline">
              Tentar novamente
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
