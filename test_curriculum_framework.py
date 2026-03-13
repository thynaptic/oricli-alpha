#!/usr/bin/env python3
"""
Test script for Cognitive Curriculum Testing Framework
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from oricli_core.evaluation.curriculum import (
            TestConfiguration,
            OptionalConstraints,
            TestResult,
            ScoringRubric,
            MemoryContinuityMode,
            SafetyPosture,
            PassFailStatus,
        )
        print("✓ Core models imported")
    except Exception as e:
        print(f"✗ Failed to import core models: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.selector import CurriculumSelector
        print("✓ Selector imported")
    except Exception as e:
        print(f"✗ Failed to import selector: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.executor import TestExecutor
        print("✓ Executor imported")
    except Exception as e:
        print(f"✗ Failed to import executor: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.analyzer import ResultAnalyzer
        print("✓ Analyzer imported")
    except Exception as e:
        print(f"✗ Failed to import analyzer: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.reporter import TestReporter
        print("✓ Reporter imported")
    except Exception as e:
        print(f"✗ Failed to import reporter: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.rubric import RubricScorer
        print("✓ Rubric scorer imported")
    except Exception as e:
        print(f"✗ Failed to import rubric scorer: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.constraints import ConstraintManager
        print("✓ Constraint manager imported")
    except Exception as e:
        print(f"✗ Failed to import constraint manager: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.generator import CurriculumGenerator
        print("✓ Generator imported")
    except Exception as e:
        print(f"✗ Failed to import generator: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.analytics import CurriculumAnalytics
        print("✓ Analytics imported")
    except Exception as e:
        print(f"✗ Failed to import analytics: {e}")
        return False
    
    try:
        from oricli_core.evaluation.curriculum.exporters import CurriculumExporter
        print("✓ Exporter imported")
    except Exception as e:
        print(f"✗ Failed to import exporter: {e}")
        return False
    
    return True


def test_data_models():
    """Test data model creation and validation"""
    print("\nTesting data models...")
    
    try:
        from oricli_core.evaluation.curriculum.models import (
            TestConfiguration,
            OptionalConstraints,
            MemoryContinuityMode,
            SafetyPosture,
            ScoringRubric,
        )
        
        # Test OptionalConstraints
        constraints = OptionalConstraints(
            time_bound=60.0,
            token_bound=1000,
            memory_continuity=MemoryContinuityMode.SHORT_TERM,
            safety_posture=SafetyPosture.NORMAL,
        )
        print(f"✓ Created OptionalConstraints: {constraints.memory_continuity}")
        
        # Test TestConfiguration
        config = TestConfiguration(
            level="k5",
            subject="math",
            skill_type="foundational",
            difficulty_style="standard",
            constraints=constraints,
        )
        print(f"✓ Created TestConfiguration: {config.level}/{config.subject}")
        
        # Test ScoringRubric
        rubric = ScoringRubric()
        score_breakdown = rubric.compute_score(
            accuracy=0.9,
            reasoning_depth=0.8,
            verbosity=0.7,
            structure=0.8,
        )
        print(f"✓ Computed score: {score_breakdown.final_score:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ Data model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_selector():
    """Test curriculum selector"""
    print("\nTesting curriculum selector...")
    
    try:
        from oricli_core.evaluation.curriculum.selector import CurriculumSelector
        
        selector = CurriculumSelector()
        
        # Test listing options
        levels = selector.list_levels()
        print(f"✓ Found {len(levels)} levels: {levels[:3]}...")
        
        subjects = selector.list_subjects()
        print(f"✓ Found {len(subjects)} subjects: {subjects[:3]}...")
        
        skill_types = selector.list_skill_types()
        print(f"✓ Found {len(skill_types)} skill types: {skill_types[:3]}...")
        
        difficulties = selector.list_difficulty_styles()
        print(f"✓ Found {len(difficulties)} difficulty styles: {difficulties[:3]}...")
        
        # Test programmatic selection
        config = selector.select_curriculum(
            level="k5",
            subject="math",
            skill_type="foundational",
            difficulty_style="standard",
        )
        print(f"✓ Selected curriculum: {config.level}/{config.subject}")
        
        return True
    except Exception as e:
        print(f"✗ Selector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_constraints():
    """Test constraint manager"""
    print("\nTesting constraint manager...")
    
    try:
        from oricli_core.evaluation.curriculum.constraints import ConstraintManager
        from oricli_core.evaluation.curriculum.models import OptionalConstraints, MemoryContinuityMode
        
        constraints = OptionalConstraints(
            time_bound=60.0,
            memory_continuity=MemoryContinuityMode.SHORT_TERM,
        )
        
        manager = ConstraintManager(constraints)
        
        # Test memory setup
        memory_config = manager.setup_memory_continuity()
        print(f"✓ Memory continuity configured: {memory_config.get('enabled')}")
        
        # Test safety posture
        safety_config = manager.get_safety_posture_config()
        print(f"✓ Safety posture configured: {safety_config.get('mode')}")
        
        return True
    except Exception as e:
        print(f"✗ Constraint manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rubric():
    """Test scoring rubric"""
    print("\nTesting scoring rubric...")
    
    try:
        from oricli_core.evaluation.curriculum.rubric import RubricScorer
        
        scorer = RubricScorer()
        
        # Test accuracy scoring
        accuracy = scorer.compute_accuracy_score(5, 5, "multiple_choice")
        print(f"✓ Accuracy score (exact match): {accuracy}")
        
        # Test reasoning depth
        reasoning_trace = {"steps": [{"reasoning": "Step 1"}, {"reasoning": "Step 2"}]}
        depth = scorer.compute_reasoning_depth_score(reasoning_trace, expected_steps=2)
        print(f"✓ Reasoning depth score: {depth:.2f}")
        
        # Test verbosity
        verbosity = scorer.compute_verbosity_score("This is a test response with multiple words", question_complexity=2)
        print(f"✓ Verbosity score: {verbosity:.2f}")
        
        # Test structure
        structure = scorer.compute_structure_score("Step 1: First point.\n\nStep 2: Second point.")
        print(f"✓ Structure score: {structure:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ Rubric test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analyzer():
    """Test result analyzer"""
    print("\nTesting result analyzer...")
    
    try:
        from oricli_core.evaluation.curriculum.analyzer import ResultAnalyzer
        from oricli_core.evaluation.curriculum.models import (
            TestResult,
            TestConfiguration,
            ScoreBreakdown,
            PassFailStatus,
        )
        
        analyzer = ResultAnalyzer()
        
        # Create a mock result
        config = TestConfiguration(
            level="k5",
            subject="math",
            skill_type="foundational",
            difficulty_style="standard",
        )
        
        score_breakdown = ScoreBreakdown(
            accuracy=0.8,
            reasoning_depth=0.7,
            verbosity=0.6,
            structure=0.7,
            final_score=0.72,
        )
        
        result = TestResult(
            test_id="test_001",
            test_config=config,
            score=0.72,
            score_breakdown=score_breakdown,
            pass_fail_status=PassFailStatus.PASS,
        )
        
        # Test weakness analysis
        weaknesses = analyzer.analyze_cognitive_weaknesses(result)
        print(f"✓ Analyzed weaknesses: {len(weaknesses)} items")
        
        # Test strength analysis
        strengths = analyzer.analyze_cognitive_strengths(result)
        print(f"✓ Analyzed strengths: {len(strengths)} items")
        
        # Test next test suggestion
        next_test = analyzer.suggest_next_test(result)
        if next_test:
            print(f"✓ Suggested next test: {next_test.difficulty_style}")
        else:
            print("✓ No next test suggested (expected for pass)")
        
        return True
    except Exception as e:
        print(f"✗ Analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reporter():
    """Test reporter"""
    print("\nTesting reporter...")
    
    try:
        from oricli_core.evaluation.curriculum.reporter import TestReporter
        from oricli_core.evaluation.curriculum.models import (
            TestResult,
            TestConfiguration,
            ScoreBreakdown,
            PassFailStatus,
        )
        
        reporter = TestReporter()
        
        # Create a mock result
        config = TestConfiguration(
            level="k5",
            subject="math",
            skill_type="foundational",
            difficulty_style="standard",
        )
        
        score_breakdown = ScoreBreakdown(
            accuracy=0.8,
            reasoning_depth=0.7,
            verbosity=0.6,
            structure=0.7,
            final_score=0.72,
        )
        
        result = TestResult(
            test_id="test_001",
            test_config=config,
            score=0.72,
            score_breakdown=score_breakdown,
            pass_fail_status=PassFailStatus.PASS,
        )
        
        # Test JSON report generation
        json_path = reporter.generate_json_report([result])
        print(f"✓ Generated JSON report: {json_path}")
        
        # Test HTML report generation
        html_path = reporter.generate_html_report([result])
        print(f"✓ Generated HTML report: {html_path}")
        
        # Verify files exist
        if json_path.exists():
            print(f"✓ JSON report file exists ({json_path.stat().st_size} bytes)")
        else:
            print(f"✗ JSON report file not found")
            return False
        
        if html_path.exists():
            print(f"✓ HTML report file exists ({html_path.stat().st_size} bytes)")
        else:
            print(f"✗ HTML report file not found")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Reporter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metadata_files():
    """Test that metadata files exist and are valid JSON"""
    print("\nTesting metadata files...")
    
    try:
        import json
        from pathlib import Path
        
        metadata_dir = Path(__file__).parent / "oricli_core" / "evaluation" / "curriculum" / "data" / "metadata"
        
        files = ["levels.json", "subjects.json", "skill_types.json", "difficulty_styles.json"]
        
        for filename in files:
            filepath = metadata_dir / filename
            if not filepath.exists():
                print(f"✗ Metadata file not found: {filename}")
                return False
            
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"✓ Loaded {filename}: {len(data.get('levels', data.get('subjects', data.get('skill_types', data.get('difficulty_styles', [])))))} items")
        
        return True
    except Exception as e:
        print(f"✗ Metadata files test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Cognitive Curriculum Testing Framework - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Data Models", test_data_models),
        ("Selector", test_selector),
        ("Constraints", test_constraints),
        ("Rubric", test_rubric),
        ("Analyzer", test_analyzer),
        ("Reporter", test_reporter),
        ("Metadata Files", test_metadata_files),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

