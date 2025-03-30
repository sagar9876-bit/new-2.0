import pytest
import time
from datetime import datetime
from performance.metrics_collector import MetricsCollector
from performance.resource_monitor import ResourceMonitor
from performance.performance_analyzer import PerformanceAnalyzer
from performance.alert_manager import AlertManager

@pytest.fixture
def metrics_collector():
    return MetricsCollector(
        collection_interval=1.0,
        max_samples=1000,
        metrics_file="logs/metrics.json"
    )

@pytest.fixture
def resource_monitor():
    return ResourceMonitor(
        check_interval=1.0,
        thresholds={
            'cpu_percent': 80.0,
            'memory_percent': 80.0,
            'disk_percent': 80.0
        }
    )

@pytest.fixture
def performance_analyzer():
    return PerformanceAnalyzer(
        window_size=10,
        threshold=0.8,
        analysis_interval=60.0
    )

@pytest.fixture
def alert_manager():
    return AlertManager(
        alert_file="logs/alerts.json",
        max_alerts=1000,
        alert_levels=['INFO', 'WARNING', 'ERROR', 'CRITICAL']
    )

def test_metrics_collector_initialization(metrics_collector):
    assert metrics_collector.collection_interval == 1.0
    assert metrics_collector.max_samples == 1000
    assert metrics_collector.metrics_file == "logs/metrics.json"
    assert metrics_collector.metrics == []
    assert metrics_collector.is_running is False

def test_metrics_collection(metrics_collector):
    # Start collection
    metrics_collector.start()
    assert metrics_collector.is_running is True
    
    # Wait for some metrics to be collected
    time.sleep(2.0)
    
    # Stop collection
    metrics_collector.stop()
    assert metrics_collector.is_running is False
    assert len(metrics_collector.metrics) > 0
    
    # Verify metric structure
    metric = metrics_collector.metrics[0]
    assert 'timestamp' in metric
    assert 'cpu_percent' in metric
    assert 'memory_percent' in metric
    assert 'disk_percent' in metric

def test_metrics_saving_loading(metrics_collector):
    # Add some test metrics
    test_metrics = [
        {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': 50.0,
            'memory_percent': 60.0,
            'disk_percent': 70.0
        }
    ]
    metrics_collector.metrics = test_metrics
    
    # Save metrics
    metrics_collector.save_metrics()
    
    # Clear metrics
    metrics_collector.metrics = []
    
    # Load metrics
    metrics_collector.load_metrics()
    assert len(metrics_collector.metrics) == 1
    assert metrics_collector.metrics[0]['cpu_percent'] == 50.0

def test_resource_monitor_initialization(resource_monitor):
    assert resource_monitor.check_interval == 1.0
    assert resource_monitor.thresholds['cpu_percent'] == 80.0
    assert resource_monitor.thresholds['memory_percent'] == 80.0
    assert resource_monitor.thresholds['disk_percent'] == 80.0
    assert resource_monitor.is_running is False

def test_resource_monitoring(resource_monitor):
    # Start monitoring
    resource_monitor.start()
    assert resource_monitor.is_running is True
    
    # Wait for some checks
    time.sleep(2.0)
    
    # Stop monitoring
    resource_monitor.stop()
    assert resource_monitor.is_running is False
    
    # Verify resource usage
    usage = resource_monitor.get_resource_usage()
    assert 'cpu_percent' in usage
    assert 'memory_percent' in usage
    assert 'disk_percent' in usage
    assert all(0 <= value <= 100 for value in usage.values())

def test_resource_threshold_checking(resource_monitor):
    # Test threshold checking
    usage = {
        'cpu_percent': 90.0,
        'memory_percent': 85.0,
        'disk_percent': 75.0
    }
    
    alerts = resource_monitor.check_thresholds(usage)
    assert len(alerts) == 2  # CPU and memory exceed thresholds
    assert all(alert['level'] == 'WARNING' for alert in alerts)

def test_performance_analyzer_initialization(performance_analyzer):
    assert performance_analyzer.window_size == 10
    assert performance_analyzer.threshold == 0.8
    assert performance_analyzer.analysis_interval == 60.0
    assert performance_analyzer.metrics == []
    assert performance_analyzer.is_running is False

def test_performance_analysis(performance_analyzer):
    # Add some test metrics
    test_metrics = [
        {'timestamp': datetime.now().isoformat(), 'value': 1.0},
        {'timestamp': datetime.now().isoformat(), 'value': 2.0},
        {'timestamp': datetime.now().isoformat(), 'value': 3.0}
    ]
    performance_analyzer.metrics = test_metrics
    
    # Analyze performance
    analysis = performance_analyzer.analyze_performance()
    assert 'mean' in analysis
    assert 'std' in analysis
    assert 'trend' in analysis
    assert 'anomalies' in analysis

def test_performance_trend_detection(performance_analyzer):
    # Add metrics with a clear trend
    test_metrics = [
        {'timestamp': datetime.now().isoformat(), 'value': i}
        for i in range(10)
    ]
    performance_analyzer.metrics = test_metrics
    
    # Detect trend
    trend = performance_analyzer.detect_trend()
    assert trend['direction'] == 'increasing'
    assert trend['strength'] > 0

def test_alert_manager_initialization(alert_manager):
    assert alert_manager.alert_file == "logs/alerts.json"
    assert alert_manager.max_alerts == 1000
    assert alert_manager.alert_levels == ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
    assert alert_manager.alerts == []

def test_alert_creation(alert_manager):
    # Create test alert
    alert = {
        'timestamp': datetime.now().isoformat(),
        'level': 'WARNING',
        'message': 'High CPU usage detected',
        'details': {'cpu_percent': 85.0}
    }
    
    # Add alert
    alert_manager.add_alert(alert)
    assert len(alert_manager.alerts) == 1
    assert alert_manager.alerts[0]['level'] == 'WARNING'
    assert alert_manager.alerts[0]['message'] == 'High CPU usage detected'

def test_alert_filtering(alert_manager):
    # Add alerts with different levels
    alerts = [
        {'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': 'Info alert'},
        {'timestamp': datetime.now().isoformat(), 'level': 'WARNING', 'message': 'Warning alert'},
        {'timestamp': datetime.now().isoformat(), 'level': 'ERROR', 'message': 'Error alert'},
        {'timestamp': datetime.now().isoformat(), 'level': 'CRITICAL', 'message': 'Critical alert'}
    ]
    
    for alert in alerts:
        alert_manager.add_alert(alert)
    
    # Filter alerts
    warning_alerts = alert_manager.get_alerts_by_level('WARNING')
    assert len(warning_alerts) == 1
    assert warning_alerts[0]['level'] == 'WARNING'
    
    critical_alerts = alert_manager.get_alerts_by_level('CRITICAL')
    assert len(critical_alerts) == 1
    assert critical_alerts[0]['level'] == 'CRITICAL'

def test_alert_saving_loading(alert_manager):
    # Add test alert
    alert = {
        'timestamp': datetime.now().isoformat(),
        'level': 'WARNING',
        'message': 'Test alert',
        'details': {}
    }
    alert_manager.add_alert(alert)
    
    # Save alerts
    alert_manager.save_alerts()
    
    # Clear alerts
    alert_manager.alerts = []
    
    # Load alerts
    alert_manager.load_alerts()
    assert len(alert_manager.alerts) == 1
    assert alert_manager.alerts[0]['level'] == 'WARNING'

def test_performance_monitoring_error_handling(metrics_collector, resource_monitor, performance_analyzer, alert_manager):
    # Test metrics collector error handling
    with pytest.raises(ValueError):
        metrics_collector.collection_interval = -1
    
    # Test resource monitor error handling
    with pytest.raises(ValueError):
        resource_monitor.thresholds['cpu_percent'] = -1
    
    # Test performance analyzer error handling
    with pytest.raises(ValueError):
        performance_analyzer.window_size = 0
    
    # Test alert manager error handling
    with pytest.raises(ValueError):
        alert_manager.add_alert({})

def test_performance_monitoring_cleanup(metrics_collector, resource_monitor, performance_analyzer, alert_manager):
    # Test cleanup
    metrics_collector.cleanup()
    resource_monitor.cleanup()
    performance_analyzer.cleanup()
    alert_manager.cleanup()
    
    # No assertions needed as we're just testing the method calls 