#!/bin/bash

set -e

. ./scripts/load_python_env.sh

echo '=== Running prepdocs.py with explicit index arguments ==='

additionalArgs=""
if [ $# -gt 0 ]; then
  additionalArgs="$@"
fi

# Create sample data directories if they don't exist
mkdir -p data/cosmic data/substrate

# Create sample cosmic data if it doesn't exist
if [ ! "$(ls -A data/cosmic/ 2>/dev/null)" ]; then
    echo "📝 Creating sample cosmic data..."
    cat > data/cosmic/cosmic_overview.md << 'EOF'
# Microsoft Cosmic Platform

## Overview
Microsoft Cosmic is a container orchestration platform optimized for performance monitoring and diagnostics.

## Key Features
- Container lifecycle management
- Real-time performance metrics
- Advanced diagnostic tools
- Resource optimization
- Automated scaling

## Performance Monitoring
Monitor your containers with:
- CPU and memory utilization tracking
- Network throughput analysis
- Storage I/O metrics
- Application-level diagnostics

## Common Issues
- High memory utilization in containers
- CPU throttling
- Network latency
- Storage bottlenecks
EOF
fi

# Create sample substrate data if it doesn't exist
if [ ! "$(ls -A data/substrate/ 2>/dev/null)" ]; then
    echo "📝 Creating sample substrate data..."
    cat > data/substrate/substrate_overview.md << 'EOF'
# Microsoft Substrate Infrastructure

## Overview  
Microsoft Substrate is an infrastructure platform for cloud services deployment and management.

## Key Features
- Infrastructure as Code (IaC)
- Automated deployment pipelines
- Scalable resource management
- Azure integration

## Infrastructure Setup
Deploy infrastructure with:
- Resource templates
- Scaling policies
- Network configuration
- Security policies

## Best Practices
- Use declarative infrastructure definitions
- Implement automated testing
- Monitor resource utilization
- Regular security audits
EOF
fi

# Process Cosmic documents
echo ""
echo "=== Processing Cosmic Documents ==="
echo "Index: cosmic-index"
echo "Agent: cosmic-agent"
echo "Data: ./data/cosmic/*"
./.venv/bin/python ./app/backend/prepdocs.py './data/cosmic/*' \
    --searchindex "cosmic-index" \
    --searchagent "cosmic-agent" \
    --category "Cosmic" \
    --verbose \
    --skip-domain-classifier \
    $additionalArgs

echo ""
echo "✅ Cosmic documents processed"

# Process Substrate documents  
echo ""
echo "=== Processing Substrate Documents ==="
echo "Index: substrate-index"
echo "Agent: substrate-agent"
echo "Data: ./data/substrate/*"
./.venv/bin/python ./app/backend/prepdocs.py "./data/substrate/*" \
    --searchindex "substrate-index" \
    --searchagent "substrate-agent" \
    --category "Substrate" \
    --verbose \
    --skip-domain-classifier \
    $additionalArgs

echo ""
echo "✅ Substrate documents processed"

# Set up domain classifier
echo ""
echo "=== Setting up Domain Classifier ==="
echo "Index: domain-classifier-index"
./.venv/bin/python ./app/backend/prepdocs.py  './data/*' \
    --searchindex "domain-classifier-index" \
    --domain-classifier-only \
    --verbose \
    $additionalArgs

echo ""
echo "✅ Domain classifier setup complete"

echo ""
echo "=== ✅ Multi-index setup complete! ==="
echo "Created/populated indexes:"
echo "  - cosmic-index (with cosmic domain data)"
echo "  - substrate-index (with substrate domain data)"  
echo "  - domain-classifier-index (with classification training data)"
echo ""
echo "Your app should now be able to:"
echo "  1. Classify questions into Cosmic or Substrate domains"
echo "  2. Route queries to the appropriate domain index"
echo "  3. Return domain-specific results"