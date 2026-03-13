from __future__ import annotations
"""
CLI Interface

Interactive menu and command-line interface for curriculum testing.
"""

import json
import sys
import warnings
from pathlib import Path
from typing import Optional

# Suppress numpy/keras deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*np.object.*")

try:
    import typer
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.table import Table
    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

from oricli_core.evaluation.curriculum.selector import CurriculumSelector
from oricli_core.evaluation.curriculum.executor import TestExecutor
from oricli_core.evaluation.curriculum.reporter import TestReporter
from oricli_core.evaluation.curriculum.models import TestConfiguration
from oricli_core.evaluation.curriculum.generator import CurriculumGenerator
from oricli_core.evaluation.curriculum.data_sources.manager import DataSourceManager


if TYPER_AVAILABLE:
    app = typer.Typer(help="OricliAlpha Curriculum Testing Framework")
    console = Console()
else:
    app = None
    console = None


def main():
    """Main entry point"""
    if not TYPER_AVAILABLE:
        print("Error: typer and rich are required for CLI. Install with: pip install typer rich")
        sys.exit(1)
    
    if app is not None:
        app()
    else:
        print("Error: CLI not available")
        sys.exit(1)


if app is not None:
    @app.command()
    def full(
        progressive: bool = typer.Option(True, "--progressive/--all", help="Use progressive difficulty testing"),
        source: Optional[str] = typer.Option(None, "--source", help="Data source to use (e.g., 'huggingface:hendrycks/MMLU', 'local')"),
    ):
        """Run full curriculum test suite"""
        console.print("[bold blue]Running Full Curriculum Test Suite[/bold blue]\n")
        
        # Show initialization progress
        console.print("[cyan]Initializing test executor...[/cyan]", end="")
        import sys
        sys.stdout.flush()
        
        executor = TestExecutor()
        console.print(" [green]OK[/green]")
        
        console.print("[cyan]Initializing reporter...[/cyan]", end="")
        sys.stdout.flush()
        reporter = TestReporter()
        console.print(" [green]OK[/green]")
        
        # Show initialization progress
        console.print("[cyan]Discovering modules...[/cyan]", end="")
        sys.stdout.flush()
        
        # Force module discovery to show progress
        from oricli_core.brain.registry import ModuleRegistry
        if not ModuleRegistry._discovered:
            console.print("[cyan]Discovering brain modules...[/cyan]")
            ModuleRegistry.discover_modules(verbose=False)
            module_count = len(ModuleRegistry.list_modules())
            console.print(f"[green]OK[/green] Discovered {module_count} modules\n")
        
        results = []
        
        if progressive:
            console.print("[cyan]Starting progressive difficulty testing...[/cyan]")
            console.print("[yellow]Tests will progress until failure or max difficulty reached[/yellow]\n")
            
            # Track progress for progressive mode
            test_count = [0]  # Use list to allow modification in nested function
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Preparing first test...[/cyan]",
                    total=None
                )
                
                # Monkey-patch execute_test to show progress
                original_execute = executor.execute_test
                
                def execute_with_progress(config, question_data=None):
                    test_count[0] += 1
                    config_str = f"{config.level}/{config.subject}/{config.skill_type}/{config.difficulty_style}"
                    progress.update(
                        task,
                        description=f"[cyan]Test {test_count[0]}: {config_str}[/cyan]"
                    )
                    try:
                        result = original_execute(config, question_data)
                        # Handle both enum and string values
                        status_value = result.pass_fail_status
                        if hasattr(status_value, 'value'):
                            status_value = status_value.value
                        status_mark = "[PASS]" if status_value == "pass" else "[FAIL]"
                        status_color = "green" if status_value == "pass" else "red"
                        progress.update(
                            task,
                            description=f"[{status_color}]{status_mark}[/{status_color}] Test {test_count[0]}: {config_str} (score: {result.score_breakdown.final_score:.2f})"
                        )
                        return result
                    except Exception as e:
                        progress.update(
                            task,
                            description=f"[red][FAIL][/red] Test {test_count[0]}: {config_str} (Error: {type(e).__name__})"
                        )
                        raise
                
                executor.execute_test = execute_with_progress
                
                try:
                    results = executor.execute_full_curriculum(progressive=progressive, source_name=source)
                finally:
                    # Restore original method
                    executor.execute_test = original_execute
                
                if results:
                    progress.update(
                        task,
                        completed=True,
                        description=f"[green]Completed {len(results)} tests[/green]"
                    )
                else:
                    progress.update(
                        task,
                        completed=True,
                        description="[yellow]No tests executed[/yellow]"
                    )
        else:
            console.print("[cyan]Running all tests in curriculum...[/cyan]\n")
            
            # Get total test count first
            console.print("[cyan]Scanning test data...[/cyan]")
            data_dir = executor.data_dir / "levels"
            total_estimate = 0
            test_files = []
            
            for level_dir in data_dir.iterdir():
                if level_dir.is_dir():
                    for subject_file in level_dir.glob("*.json"):
                        try:
                            with open(subject_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                question_count = len(data.get("questions", []))
                                total_estimate += question_count
                                if question_count > 0:
                                    test_files.append((level_dir.name, subject_file.stem, question_count))
                        except Exception:
                            pass
            
            if total_estimate == 0:
                console.print("[yellow]WARNING: No test questions found in data directory[/yellow]")
                console.print("[yellow]Run 'oricli-curriculum-test generate' to create test data[/yellow]")
                return
            
            console.print(f"[green]OK[/green] Found {total_estimate} test questions across {len(test_files)} files\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Executing tests...[/cyan]",
                    total=total_estimate
                )
                
                # Track progress
                test_count = [0]  # Use list to allow modification in nested function
                
                # Monkey-patch execute_test to show progress
                original_execute = executor.execute_test
                
                def execute_with_progress(config, question_data=None):
                    test_count[0] += 1
                    config_str = f"{config.level}/{config.subject}"
                    try:
                        progress.update(
                            task,
                            completed=test_count[0],
                            description=f"[cyan]RUNNING Test {test_count[0]}/{total_estimate}: {config_str}[/cyan]"
                        )
                        result = original_execute(config, question_data)
                        
                        # Update with result
                        # Handle both enum and string values
                        status_value = result.pass_fail_status
                        if hasattr(status_value, 'value'):
                            status_value = status_value.value
                        status_mark = "[PASS]" if status_value == "pass" else "[FAIL]"
                        status_color = "green" if status_value == "pass" else "red"
                        progress.update(
                            task,
                            completed=test_count[0],
                            description=f"[{status_color}]{status_mark}[/{status_color}] Test {test_count[0]}/{total_estimate}: {config_str} (score: {result.score_breakdown.final_score:.2f})"
                        )
                        return result
                    except Exception as e:
                        progress.update(
                            task,
                            completed=test_count[0],
                            description=f"[red][FAIL][/red] Test {test_count[0]}/{total_estimate}: {config_str} (Error)"
                        )
                        raise
                
                executor.execute_test = execute_with_progress
                
                try:
                    results = executor.execute_full_curriculum(progressive=progressive, source_name=source)
                finally:
                    # Restore original method
                    executor.execute_test = original_execute
                
                progress.update(
                    task,
                    completed=len(results) if results else test_count[0],
                    description=f"[green]Completed {len(results)} tests[/green]"
                )
        
        # Check if any tests were run
        if not results:
            console.print("\n[bold yellow]WARNING: No tests were executed.[/bold yellow]")
            console.print("[yellow]This usually means no test questions are available.[/yellow]")
            console.print("\n[yellow]To generate test data, run:[/yellow]")
            console.print("[cyan]  oricli-curriculum-test generate[/cyan]")
            console.print("\n[yellow]Or generate for a specific level:[/yellow]")
            console.print("[cyan]  oricli-curriculum-test generate --level k5[/cyan]")
            return
        
        # Generate reports
        console.print("\n[bold green]Generating reports...[/bold green]")
        json_path = reporter.generate_json_report(results)
        html_path = reporter.generate_html_report(results)
        
        console.print(f"\n[bold green]OK[/bold green] JSON report: {json_path}")
        console.print(f"[bold green]OK[/bold green] HTML report: {html_path}")
        
        # Print summary
        from oricli_core.evaluation.curriculum.analyzer import ResultAnalyzer
        analyzer = ResultAnalyzer()
        summary = analyzer.analyze_batch(results)
        
        console.print("\n[bold blue]Summary:[/bold blue]")
        console.print(f"  Total Tests: {summary['total_tests']}")
        console.print(f"  Passed: {summary['passed']} ({summary['pass_rate']*100:.1f}%)")
        console.print(f"  Failed: {summary['failed']}")
        console.print(f"  Partial: {summary['partial']}")
        console.print(f"  Average Score: {summary['average_score']:.2f}")

    @app.command()
    def select():
        """Interactive curriculum selection"""
        console.print("[bold blue]Cognitive Curriculum Selector[/bold blue]\n")
        
        selector = CurriculumSelector()
        config = selector.select_interactive()
        
        console.print("\n[bold green]Executing selected test...[/bold green]")
        config_str = f"{config.level}/{config.subject}/{config.skill_type}/{config.difficulty_style}"
        console.print(f"[cyan]Configuration: {config_str}[/cyan]\n")
        
        executor = TestExecutor()
        reporter = TestReporter()
        
        # Show progress during execution
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"[cyan]Executing test: {config_str}...[/cyan]", total=None)
            
            result = executor.execute_test(config)
            
            # Update with result
            # Handle both enum and string values
            status_value = result.pass_fail_status
            if hasattr(status_value, 'value'):
                status_value = status_value.value
            status_mark = "[PASS]" if status_value == "pass" else "[FAIL]"
            status_color = "green" if status_value == "pass" else "red"
            progress.update(
                task,
                completed=True,
                description=f"[{status_color}]{status_mark}[/{status_color}] Test completed (score: {result.score_breakdown.final_score:.2f})"
            )
        
        results = [result]
        
        # Generate reports
        console.print("\n[bold green]Generating reports...[/bold green]")
        json_path = reporter.generate_json_report(results)
        html_path = reporter.generate_html_report(results)
        
        console.print(f"\n[bold green]OK[/bold green] JSON report: {json_path}")
        console.print(f"[bold green]OK[/bold green] HTML report: {html_path}")
        
        # Print result
        console.print("\n[bold blue]Test Result:[/bold blue]")
        # Handle both enum and string values
        status_value = result.pass_fail_status
        if hasattr(status_value, 'value'):
            status_value = status_value.value
        status_color = "green" if status_value == "pass" else "red" if status_value == "fail" else "yellow"
        console.print(f"  Status: [{status_color}]{str(status_value).upper()}[/{status_color}]")
        console.print(f"  Score: {result.score_breakdown.final_score:.2f}")
        console.print(f"  Execution Time: {result.execution_time:.2f}s")
        
        if result.error_message:
            console.print(f"  [red]Error: {result.error_message}[/red]")

    @app.command()
    def config(
        config_file: Path = typer.Argument(..., help="Configuration file path"),
    ):
        """Run test from configuration file"""
        import json
        
        console.print(f"[bold blue]Loading configuration from {config_file}[/bold blue]\n")
        
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        config = TestConfiguration.from_dict(config_data)
        
        console.print("[bold green]Executing test...[/bold green]\n")
        
        executor = TestExecutor()
        reporter = TestReporter()
        
        result = executor.execute_test(config)
        results = [result]
        
        # Generate reports
        json_path = reporter.generate_json_report(results)
        html_path = reporter.generate_html_report(results)
        
        console.print(f"\n[bold green]OK[/bold green] JSON report: {json_path}")
        console.print(f"[bold green]OK[/bold green] HTML report: {html_path}")

    @app.command()
    def direct(
        level: str = typer.Option(..., "--level", help="Education level"),
        subject: str = typer.Option(..., "--subject", help="Subject domain"),
        skill_type: str = typer.Option(..., "--skill-type", help="Skill type"),
        difficulty_style: str = typer.Option(..., "--difficulty", help="Difficulty style"),
    ):
        """Run test with direct parameter selection"""
        selector = CurriculumSelector()
        config = selector.select_curriculum(
            level=level,
            subject=subject,
            skill_type=skill_type,
            difficulty_style=difficulty_style,
        )
        
        console.print("[bold green]Executing test...[/bold green]\n")
        
        executor = TestExecutor()
        reporter = TestReporter()
        
        result = executor.execute_test(config)
        results = [result]
        
        # Generate reports
        json_path = reporter.generate_json_report(results)
        html_path = reporter.generate_html_report(results)
        
        console.print(f"\n[bold green]OK[/bold green] JSON report: {json_path}")
        console.print(f"[bold green]OK[/bold green] HTML report: {html_path}")

    @app.command()
    def generate(
        output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Output directory for generated test data"),
        level: Optional[str] = typer.Option(None, "--level", help="Generate data for specific level only"),
    ):
        """Generate test dataset"""
        from pathlib import Path
        
        if output_dir is None:
            output_dir = Path(__file__).parent / "data"
        else:
            output_dir = Path(output_dir)
        
        console.print(f"[bold blue]Generating test dataset...[/bold blue]\n")
        console.print(f"Output directory: {output_dir}\n")
        
        generator = CurriculumGenerator()
        
        if level:
            console.print(f"Generating data for level: {level}")
            generator.generate_level(level, output_dir)
        else:
            console.print("Generating full curriculum dataset...")
            generator.generate_full_curriculum(output_dir)
        
        console.print("\n[bold green]OK[/bold green] Test dataset generated successfully!")
        console.print(f"[green]Data saved to: {output_dir}[/green]")

    @app.command()
    def list_sources():
        """List all available data sources"""
        console.print("[bold blue]Available Data Sources[/bold blue]\n")
        
        manager = DataSourceManager()
        sources = manager.list_sources()
        
        if not sources:
            console.print("[yellow]No data sources available[/yellow]")
            return
        
        table = Table(title="Data Sources")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        
        for source_name in sources:
            source = manager.get_source(source_name)
            if source:
                source_type = source_name.split(":")[0] if ":" in source_name else source_name
                table.add_row(source_name, source_type)
        
        console.print(table)
        console.print("\n[dim]Use --source option to specify a source when running tests[/dim]")
        console.print("[dim]Example: oricli-curriculum-test full --source huggingface:hendrycks/MMLU[/dim]")
    
    @app.command()
    def web_ui(
        host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
        port: int = typer.Option(8080, "--port", help="Port to bind to"),
    ):
        """Start web UI server"""
        console.print(f"[bold blue]Starting Web UI server on {host}:{port}[/bold blue]\n")
        
        try:
            from oricli_core.evaluation.curriculum.web_ui.server import start_web_ui
            start_web_ui(host=host, port=port)
        except ImportError:
            console.print("[bold red]Error: Web UI not yet implemented[/bold red]")
            sys.exit(1)


if __name__ == "__main__":
    main()
