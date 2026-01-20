#!/bin/bash
# CMS Question Bank Smoke Test Script
# Tests the full CMS workflow: create, submit, approve, publish, versioning, audit, media
#
# Required environment variables:
#   BASE_URL (default: http://localhost:8000)
#   ADMIN_EMAIL (default: admin@example.com)
#   ADMIN_PASSWORD (default: Admin123!)
#   REVIEWER_EMAIL (default: reviewer@example.com)
#   REVIEWER_PASSWORD (default: Reviewer123!)
#
# Example usage:
#   BASE_URL=http://localhost:8000 ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=Admin123! \
#   REVIEWER_EMAIL=reviewer@example.com REVIEWER_PASSWORD=Reviewer123! \
#   ./backend/scripts/smoke_cms.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Defaults
BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin123!}"
REVIEWER_EMAIL="${REVIEWER_EMAIL:-reviewer@example.com}"
REVIEWER_PASSWORD="${REVIEWER_PASSWORD:-Reviewer123!}"

# Check dependencies
if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is required but not installed${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    exit 1
fi

echo -e "${GREEN}=== CMS Question Bank Smoke Test ===${NC}"
echo "Base URL: $BASE_URL"
echo "Admin: $ADMIN_EMAIL"
echo "Reviewer: $REVIEWER_EMAIL"
echo ""

# Helper function to make authenticated requests
auth_request() {
    local method=$1
    local url=$2
    local token=$3
    local data=${4:-}
    
    if [ -n "$data" ]; then
        curl -s -X "$method" "$url" \
            -H "Authorization: Bearer $token" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$url" \
            -H "Authorization: Bearer $token"
    fi
}

# Helper function to check response
check_response() {
    local response=$1
    local expected_status=${2:-200}
    local error_msg=${3:-"Request failed"}
    
    local status_code=$(echo "$response" | jq -r '.error.code // "OK"' 2>/dev/null || echo "OK")
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/health" 2>/dev/null || echo "000")
    
    if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
        echo -e "${RED}✗ $error_msg${NC}"
        echo "$response" | jq '.'
        return 1
    fi
    
    return 0
}

# Step 1: Health checks
echo -e "${YELLOW}[1/19] Health checks...${NC}"
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | jq -e '.status == "ok"' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi

READY=$(curl -s "$BASE_URL/ready")
if echo "$READY" | jq -e '.status' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Readiness check passed${NC}"
else
    echo -e "${RED}✗ Readiness check failed${NC}"
    exit 1
fi

# Step 2: Login as ADMIN
echo -e "${YELLOW}[2/19] Login as ADMIN...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")

if echo "$LOGIN_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Admin login failed${NC}"
    echo "$LOGIN_RESPONSE" | jq '.'
    exit 1
fi

ADMIN_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.tokens.access_token')
if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}✗ Failed to extract admin token${NC}"
    echo "$LOGIN_RESPONSE" | jq '.'
    exit 1
fi
echo -e "${GREEN}✓ Admin logged in${NC}"

# Step 3: Get syllabus structure (year, block, theme IDs)
echo -e "${YELLOW}[3/19] Fetching syllabus structure...${NC}"
YEARS_RESPONSE=$(auth_request "GET" "$BASE_URL/v1/syllabus/years" "$ADMIN_TOKEN")
YEAR_ID=$(echo "$YEARS_RESPONSE" | jq -r '.[0].id // empty')
if [ -z "$YEAR_ID" ]; then
    echo -e "${RED}✗ No years found. Please seed syllabus structure first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found year ID: $YEAR_ID${NC}"

BLOCKS_RESPONSE=$(auth_request "GET" "$BASE_URL/v1/syllabus/blocks?year=$YEAR_ID" "$ADMIN_TOKEN")
BLOCK_ID=$(echo "$BLOCKS_RESPONSE" | jq -r '.[0].id // empty')
if [ -z "$BLOCK_ID" ]; then
    echo -e "${RED}✗ No blocks found for year $YEAR_ID${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found block ID: $BLOCK_ID${NC}"

THEMES_RESPONSE=$(auth_request "GET" "$BASE_URL/v1/syllabus/themes?block_id=$BLOCK_ID" "$ADMIN_TOKEN")
THEME_ID=$(echo "$THEMES_RESPONSE" | jq -r '.[0].id // empty')
if [ -z "$THEME_ID" ]; then
    echo -e "${RED}✗ No themes found for block $BLOCK_ID${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found theme ID: $THEME_ID${NC}"

# Step 4: Create DRAFT question (minimal)
echo -e "${YELLOW}[4/19] Create DRAFT question...${NC}"
CREATE_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions" "$ADMIN_TOKEN" \
    "{\"stem\":\"What is 2+2?\",\"option_a\":\"3\",\"option_b\":\"4\",\"option_c\":\"5\",\"option_d\":\"6\",\"option_e\":\"7\",\"correct_index\":1}")

if echo "$CREATE_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Failed to create question${NC}"
    echo "$CREATE_RESPONSE" | jq '.'
    exit 1
fi

QUESTION_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')
if [ "$QUESTION_ID" == "null" ] || [ -z "$QUESTION_ID" ]; then
    echo -e "${RED}✗ Failed to extract question ID${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Question created: $QUESTION_ID${NC}"

# Verify status is DRAFT
STATUS=$(echo "$CREATE_RESPONSE" | jq -r '.status')
if [ "$STATUS" != "DRAFT" ]; then
    echo -e "${RED}✗ Expected status DRAFT, got $STATUS${NC}"
    exit 1
fi

# Step 5: Try submit too early (should fail)
echo -e "${YELLOW}[5/19] Try submit without required fields (should fail)...${NC}"
SUBMIT_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions/$QUESTION_ID/submit" "$ADMIN_TOKEN")
if echo "$SUBMIT_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    ERROR_CODE=$(echo "$SUBMIT_RESPONSE" | jq -r '.error.code // "UNKNOWN"')
    if [ "$ERROR_CODE" == "HTTP_ERROR" ] || [ "$ERROR_CODE" == "VALIDATION_ERROR" ]; then
        echo -e "${GREEN}✓ Submit correctly rejected (missing required fields)${NC}"
    else
        echo -e "${YELLOW}⚠ Submit failed with unexpected error code: $ERROR_CODE${NC}"
    fi
else
    echo -e "${RED}✗ Submit should have failed but succeeded${NC}"
    exit 1
fi

# Step 6: Update question to satisfy submit gate
echo -e "${YELLOW}[6/19] Update question with required fields...${NC}"
UPDATE_RESPONSE=$(auth_request "PUT" "$BASE_URL/v1/admin/questions/$QUESTION_ID" "$ADMIN_TOKEN" \
    "{\"stem\":\"What is 2+2?\",\"option_a\":\"3\",\"option_b\":\"4\",\"option_c\":\"5\",\"option_d\":\"6\",\"option_e\":\"7\",\"correct_index\":1,\"year_id\":$YEAR_ID,\"block_id\":$BLOCK_ID,\"theme_id\":$THEME_ID,\"difficulty\":\"easy\",\"cognitive_level\":\"recall\"}")

if echo "$UPDATE_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Failed to update question${NC}"
    echo "$UPDATE_RESPONSE" | jq '.'
    exit 1
fi
echo -e "${GREEN}✓ Question updated${NC}"

# Step 7: Submit success
echo -e "${YELLOW}[7/19] Submit question for review...${NC}"
SUBMIT_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions/$QUESTION_ID/submit" "$ADMIN_TOKEN")
if echo "$SUBMIT_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Submit failed${NC}"
    echo "$SUBMIT_RESPONSE" | jq '.'
    exit 1
fi

NEW_STATUS=$(echo "$SUBMIT_RESPONSE" | jq -r '.new_status')
if [ "$NEW_STATUS" != "IN_REVIEW" ]; then
    echo -e "${RED}✗ Expected status IN_REVIEW, got $NEW_STATUS${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Question submitted (status: IN_REVIEW)${NC}"

# Step 8: Login as REVIEWER
echo -e "${YELLOW}[8/19] Login as REVIEWER...${NC}"
REVIEWER_LOGIN=$(curl -s -X POST "$BASE_URL/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$REVIEWER_EMAIL\",\"password\":\"$REVIEWER_PASSWORD\"}")

if echo "$REVIEWER_LOGIN" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Reviewer login failed${NC}"
    echo "$REVIEWER_LOGIN" | jq '.'
    exit 1
fi

REVIEWER_TOKEN=$(echo "$REVIEWER_LOGIN" | jq -r '.tokens.access_token')
if [ "$REVIEWER_TOKEN" == "null" ] || [ -z "$REVIEWER_TOKEN" ]; then
    echo -e "${RED}✗ Failed to extract reviewer token${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Reviewer logged in${NC}"

# Step 9: Approve should fail (missing explanation)
echo -e "${YELLOW}[9/19] Try approve without explanation (should fail)...${NC}"
APPROVE_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions/$QUESTION_ID/approve" "$REVIEWER_TOKEN")
if echo "$APPROVE_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Approve correctly rejected (missing explanation)${NC}"
else
    echo -e "${RED}✗ Approve should have failed but succeeded${NC}"
    exit 1
fi

# Step 10: Add explanation
echo -e "${YELLOW}[10/19] Add explanation...${NC}"
UPDATE_RESPONSE=$(auth_request "PUT" "$BASE_URL/v1/admin/questions/$QUESTION_ID" "$REVIEWER_TOKEN" \
    "{\"explanation_md\":\"2+2 equals 4 because addition of two and two results in four.\"}")

if echo "$UPDATE_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Failed to add explanation${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Explanation added${NC}"

# Step 11: Approve success
echo -e "${YELLOW}[11/19] Approve question...${NC}"
APPROVE_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions/$QUESTION_ID/approve" "$REVIEWER_TOKEN")
if echo "$APPROVE_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Approve failed${NC}"
    echo "$APPROVE_RESPONSE" | jq '.'
    exit 1
fi

NEW_STATUS=$(echo "$APPROVE_RESPONSE" | jq -r '.new_status')
if [ "$NEW_STATUS" != "APPROVED" ]; then
    echo -e "${RED}✗ Expected status APPROVED, got $NEW_STATUS${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Question approved (status: APPROVED)${NC}"

# Step 12: Publish should fail (missing source)
echo -e "${YELLOW}[12/19] Try publish without source (should fail)...${NC}"
PUBLISH_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions/$QUESTION_ID/publish" "$ADMIN_TOKEN")
if echo "$PUBLISH_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Publish correctly rejected (missing source)${NC}"
else
    echo -e "${RED}✗ Publish should have failed but succeeded${NC}"
    exit 1
fi

# Step 13: Add source fields
echo -e "${YELLOW}[13/19] Add source fields...${NC}"
UPDATE_RESPONSE=$(auth_request "PUT" "$BASE_URL/v1/admin/questions/$QUESTION_ID" "$ADMIN_TOKEN" \
    "{\"source_book\":\"Test Mathematics Book\",\"source_page\":\"p. 42\",\"source_ref\":\"TEST-001\"}")

if echo "$UPDATE_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Failed to add source fields${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Source fields added${NC}"

# Step 14: Publish success
echo -e "${YELLOW}[14/19] Publish question...${NC}"
PUBLISH_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions/$QUESTION_ID/publish" "$ADMIN_TOKEN")
if echo "$PUBLISH_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Publish failed${NC}"
    echo "$PUBLISH_RESPONSE" | jq '.'
    exit 1
fi

NEW_STATUS=$(echo "$PUBLISH_RESPONSE" | jq -r '.new_status')
if [ "$NEW_STATUS" != "PUBLISHED" ]; then
    echo -e "${RED}✗ Expected status PUBLISHED, got $NEW_STATUS${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Question published (status: PUBLISHED)${NC}"

# Step 15: RBAC test - REVIEWER cannot unpublish
echo -e "${YELLOW}[15/19] RBAC test: REVIEWER cannot unpublish...${NC}"
UNPUBLISH_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions/$QUESTION_ID/unpublish" "$REVIEWER_TOKEN")
if echo "$UNPUBLISH_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/admin/questions/$QUESTION_ID/unpublish" \
        -H "Authorization: Bearer $REVIEWER_TOKEN")
    if [ "$HTTP_CODE" == "403" ]; then
        echo -e "${GREEN}✓ Reviewer correctly denied unpublish (403)${NC}"
    else
        echo -e "${YELLOW}⚠ Reviewer denied but with unexpected status: $HTTP_CODE${NC}"
    fi
else
    echo -e "${RED}✗ Reviewer should not be able to unpublish${NC}"
    exit 1
fi

# Step 16: Unpublish success (ADMIN)
echo -e "${YELLOW}[16/19] Unpublish question (ADMIN)...${NC}"
UNPUBLISH_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/questions/$QUESTION_ID/unpublish" "$ADMIN_TOKEN")
if echo "$UNPUBLISH_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Unpublish failed${NC}"
    echo "$UNPUBLISH_RESPONSE" | jq '.'
    exit 1
fi

NEW_STATUS=$(echo "$UNPUBLISH_RESPONSE" | jq -r '.new_status')
if [ "$NEW_STATUS" != "APPROVED" ]; then
    echo -e "${RED}✗ Expected status APPROVED, got $NEW_STATUS${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Question unpublished (status: APPROVED)${NC}"

# Step 17: Check versions
echo -e "${YELLOW}[17/19] Check version history...${NC}"
VERSIONS_RESPONSE=$(auth_request "GET" "$BASE_URL/v1/admin/questions/$QUESTION_ID/versions" "$ADMIN_TOKEN")
if echo "$VERSIONS_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}✗ Failed to get versions${NC}"
    exit 1
fi

VERSION_COUNT=$(echo "$VERSIONS_RESPONSE" | jq 'length')
if [ "$VERSION_COUNT" -lt 5 ]; then
    echo -e "${YELLOW}⚠ Expected at least 5 versions, got $VERSION_COUNT${NC}"
else
    echo -e "${GREEN}✓ Found $VERSION_COUNT versions${NC}"
fi

# Check version numbers increment
FIRST_VERSION=$(echo "$VERSIONS_RESPONSE" | jq -r '.[0].version_no')
LAST_VERSION=$(echo "$VERSIONS_RESPONSE" | jq -r '.[-1].version_no')
if [ "$FIRST_VERSION" -gt "$LAST_VERSION" ]; then
    echo -e "${GREEN}✓ Version numbers increment correctly (latest: $FIRST_VERSION, first: $LAST_VERSION)${NC}"
else
    echo -e "${YELLOW}⚠ Version ordering may be incorrect${NC}"
fi

# Step 18: Check audit log
echo -e "${YELLOW}[18/19] Check audit log...${NC}"
AUDIT_RESPONSE=$(auth_request "GET" "$BASE_URL/v1/admin/audit?entity_type=QUESTION&entity_id=$QUESTION_ID&limit=20" "$ADMIN_TOKEN")
if echo "$AUDIT_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Audit endpoint not available (dev-only)${NC}"
else
    AUDIT_COUNT=$(echo "$AUDIT_RESPONSE" | jq 'length')
    if [ "$AUDIT_COUNT" -ge 5 ]; then
        echo -e "${GREEN}✓ Found $AUDIT_COUNT audit entries${NC}"
        
        # Check for key actions
        HAS_CREATE=$(echo "$AUDIT_RESPONSE" | jq '[.[] | select(.action == "question.create")] | length > 0')
        HAS_PUBLISH=$(echo "$AUDIT_RESPONSE" | jq '[.[] | select(.action == "question.publish")] | length > 0')
        if [ "$HAS_CREATE" == "true" ] && [ "$HAS_PUBLISH" == "true" ]; then
            echo -e "${GREEN}✓ Key audit actions present (create, publish)${NC}"
        else
            echo -e "${YELLOW}⚠ Some expected audit actions missing${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Expected at least 5 audit entries, got $AUDIT_COUNT${NC}"
    fi
fi

# Step 19: Media upload and attach (optional - create a small test image)
echo -e "${YELLOW}[19/19] Test media upload and attach...${NC}"
# Create a minimal 1x1 PNG image (base64 encoded)
PNG_BASE64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
echo "$PNG_BASE64" | base64 -d > /tmp/test_image.png 2>/dev/null || echo -e "${YELLOW}⚠ Could not create test image, skipping media test${NC}"

if [ -f /tmp/test_image.png ]; then
    UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/admin/media" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -F "file=@/tmp/test_image.png")
    
    if echo "$UPLOAD_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Media upload failed (may not be critical)${NC}"
    else
        MEDIA_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.id')
        if [ "$MEDIA_ID" != "null" ] && [ -n "$MEDIA_ID" ]; then
            echo -e "${GREEN}✓ Media uploaded: $MEDIA_ID${NC}"
            
            # Test SHA256 dedup - upload same file again
            UPLOAD2_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/admin/media" \
                -H "Authorization: Bearer $ADMIN_TOKEN" \
                -F "file=@/tmp/test_image.png")
            MEDIA_ID2=$(echo "$UPLOAD2_RESPONSE" | jq -r '.id')
            if [ "$MEDIA_ID" == "$MEDIA_ID2" ]; then
                echo -e "${GREEN}✓ SHA256 deduplication works (same media_id returned)${NC}"
            else
                echo -e "${YELLOW}⚠ Deduplication may not be working (different IDs)${NC}"
            fi
            
            # Attach to question
            ATTACH_RESPONSE=$(auth_request "POST" "$BASE_URL/v1/admin/media/questions/$QUESTION_ID/attach" "$ADMIN_TOKEN" \
                "{\"media_id\":\"$MEDIA_ID\",\"role\":\"STEM\"}")
            
            if echo "$ATTACH_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
                echo -e "${YELLOW}⚠ Media attach failed${NC}"
            else
                echo -e "${GREEN}✓ Media attached to question${NC}"
            fi
        fi
    fi
    rm -f /tmp/test_image.png
fi

# Final summary
echo ""
echo -e "${GREEN}=== Smoke Test Complete ===${NC}"
echo -e "${GREEN}All critical tests passed!${NC}"
echo ""
echo "Question ID: $QUESTION_ID"
echo "Status flow: DRAFT → IN_REVIEW → APPROVED → PUBLISHED → APPROVED"
echo ""
