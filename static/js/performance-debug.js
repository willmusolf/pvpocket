// Performance debugging utility for Pokemon TCG Pocket
class PerformanceDebugger {
    constructor() {
        this.marks = {};
        this.measures = [];
        this.enabled = true;
    }

    mark(name) {
        if (!this.enabled) return;
        this.marks[name] = performance.now();
        console.log(`⏱️ Mark: ${name}`);
    }

    measure(name, startMark, endMark) {
        if (!this.enabled) return;
        
        const start = this.marks[startMark] || 0;
        const end = endMark ? this.marks[endMark] : performance.now();
        const duration = end - start;
        
        this.measures.push({ name, duration, start, end });
        console.log(`📊 ${name}: ${duration.toFixed(2)}ms`);
        
        return duration;
    }

    measureNetwork() {
        if (!this.enabled || !window.performance || !window.performance.getEntriesByType) return;
        
        const resources = window.performance.getEntriesByType('resource');
        const images = resources.filter(r => r.name.includes('cdn.pvpocket.xyz') || r.name.includes('.png') || r.name.includes('.jpg'));
        
        console.log('🌐 Network Performance:');
        console.log(`Total resources: ${resources.length}`);
        console.log(`Images: ${images.length}`);
        
        // Group by status
        const cached = images.filter(img => img.transferSize === 0 || img.duration < 50);
        const slow = images.filter(img => img.duration > 200);
        
        console.log(`Cached images: ${cached.length}`);
        console.log(`Slow images (>200ms): ${slow.length}`);
        
        if (slow.length > 0) {
            console.log('Slow images:', slow.map(img => ({
                url: img.name.split('/').pop(),
                duration: img.duration.toFixed(0) + 'ms',
                size: (img.transferSize / 1024).toFixed(1) + 'KB'
            })));
        }
    }

    report() {
        if (!this.enabled) return;
        
        console.log('\n📈 Performance Report:');
        console.log('='.repeat(50));
        
        // Sort by duration
        const sorted = [...this.measures].sort((a, b) => b.duration - a.duration);
        
        // Total time
        const totalTime = performance.now();
        console.log(`Total page load time: ${totalTime.toFixed(0)}ms`);
        
        // Top time consumers
        console.log('\nTop time consumers:');
        sorted.slice(0, 10).forEach(measure => {
            const percent = (measure.duration / totalTime * 100).toFixed(1);
            console.log(`- ${measure.name}: ${measure.duration.toFixed(0)}ms (${percent}%)`);
        });
        
        // Network analysis
        this.measureNetwork();
        
        // DOM metrics
        console.log('\n📄 DOM Metrics:');
        console.log(`DOM nodes: ${document.getElementsByTagName('*').length}`);
        console.log(`Images: ${document.images.length}`);
        console.log(`Stylesheets: ${document.styleSheets.length}`);
        
        // Memory usage (if available)
        if (performance.memory) {
            console.log('\n💾 Memory Usage:');
            console.log(`Used JS Heap: ${(performance.memory.usedJSHeapSize / 1048576).toFixed(1)}MB`);
            console.log(`Total JS Heap: ${(performance.memory.totalJSHeapSize / 1048576).toFixed(1)}MB`);
        }
    }

    // Attach to window load events
    attachToPageLoad() {
        // Track DOMContentLoaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.mark('DOMContentLoaded');
                this.measure('DOM parsing', 'navigationStart', 'DOMContentLoaded');
            });
        }

        // Track window load
        window.addEventListener('load', () => {
            this.mark('windowLoad');
            this.measure('Full page load', 'navigationStart', 'windowLoad');
            
            // Report after a short delay to catch any async operations
            setTimeout(() => this.report(), 1000);
        });
    }
}

// Create global instance
window.perfDebug = new PerformanceDebugger();
window.perfDebug.mark('navigationStart');

// Auto-attach to page load
window.perfDebug.attachToPageLoad();

// Export for use in other scripts
window.PerformanceDebugger = PerformanceDebugger;