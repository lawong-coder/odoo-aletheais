# Odoo 18 CE - Singapore IRAS GST Configuration Guide

**Date:** February 18, 2026  
**Purpose:** Reference guide for configuring Odoo 18 Community Edition for Singapore GST compliance

---

## Table of Contents
1. [Overview](#overview)
2. [Community vs Enterprise Limitations](#community-vs-enterprise-limitations)
3. [Complete Configuration Steps](#complete-configuration-steps)
4. [Fiscal Positions Explained](#fiscal-positions-explained)
5. [Healthcare/Nursing Home Specific GST Treatment](#healthcarenursing-home-specific-gst-treatment)
6. [Tax Report Availability in CE](#tax-report-availability-in-ce)
7. [OCA Modules for Tax Reporting](#oca-modules-for-tax-reporting)
8. [Key Takeaways](#key-takeaways)

---

## Overview

### Current GST Rate (2025)
- **Standard Rate:** 9% (effective from 1 January 2024)

### Critical CE Limitation
- **IRAS Audit File (IAF)** is only available in Odoo **Enterprise** via `l10n_sg_reports` module
- GST F5/F7 reports are Enterprise-only
- CE has generic tax reporting only

---

## Community vs Enterprise Limitations

| Feature | Community Edition (l10n_sg) | Enterprise Edition (l10n_sg_reports) |
|---------|----------------------------|-------------------------------------|
| Singapore Chart of Accounts | ✅ Yes | ✅ Yes |
| Tax Codes (SR, ZR, TX, etc.) | ✅ Pre-configured | ✅ Pre-configured |
| GST Tracking | ✅ Automatic | ✅ Automatic |
| Generic Tax Report | ✅ Basic summary | ✅ Advanced |
| GST F5 Report (IRAS format) | ❌ Manual | ✅ Auto-generated |
| GST F7 Report | ❌ Manual | ✅ Auto-generated |
| IRAS Audit File (IAF) | ❌ Manual export | ✅ One-click export |
| Box 1-7 Mapping | ❌ Manual | ✅ Automatic |

---

## Complete Configuration Steps

### Step 1: Install Singapore Fiscal Localization

**Location:** Apps → Search "Singapore" → Install **Singapore - Accounting (`l10n_sg`)**

- Automatically installs Singapore COA
- Pre-configured tax templates
- Activates based on company country setting

---

### Step 2: Company Setup

**Location:** Settings → Companies → [Your Company]

Configure:
- **Country:** Singapore
- **Currency:** SGD
- **GST Registration Number:** Enter in VAT field (UEN + GST Reg No)
- **Company Address:** Required on tax invoices

---

### Step 3: Configure GST Rate at 9%

**Location:** Accounting → Configuration → Taxes

Verify/activate these tax codes:

| Tax Code | Description | Type | Rate |
|----------|-------------|------|------|
| **SR** | Standard Rated Supply | Sales | 9% |
| **ZR** | Zero Rated Supply (exports) | Sales | 0% |
| **ES** | Exempt Supply (financial services, residential property) | Sales | 0% |
| **OS** | Out-of-Scope | Sales | 0% |
| **TX** | Taxable Purchase (from GST-registered supplier) | Purchase | 9% |
| **ZP** | Zero Rated Purchase | Purchase | 0% |
| **EP** | Exempt Purchase | Purchase | 0% |
| **IM** | Import GST (payable to Singapore Customs) | Purchase | 9% |
| **BL** | Blocked Input Tax (Reg 26/27 - motor cars, entertainment) | Purchase | 9% |
| **NR** | Non-claimable - exempt supplies | Purchase | 9% |
| **RC** | Reverse Charge (imported services from overseas) | Purchase | 9% |

**To activate inactive taxes:** Accounting → Configuration → Taxes → Toggle Active column

---

### Step 4: Chart of Accounts Verification

**Location:** Accounting → Configuration → Chart of Accounts

Key accounts to verify:
- **GST Output Tax Payable** (Liability)
- **GST Input Tax Claimable** (Asset)
- **GST Payable/Claimable (net)** - settlement account

Singapore localization creates these automatically.

---

### Step 5: Tax-Compliant Invoice Configuration

IRAS requires these fields on every **Tax Invoice**:
- The words "Tax Invoice"
- Company name, address, and GST registration number
- Sequential invoice number
- Date of issue
- Customer's name and address (B2B)
- Description of goods/services
- Total amount excluding GST, GST amount, and total including GST
- GST rate applied

**Foreign currency invoices:** Must convert to SGD using IRAS-approved exchange rates

---

### Step 6: Fiscal Positions Setup

**Location:** Accounting → Configuration → Fiscal Positions

#### What Fiscal Positions Do:
- **Automation for "WHO"** - automatically apply correct taxes based on customer/vendor
- Change taxes based on location, GST registration status, etc.
- Optional but highly recommended for exports/imports

#### Example Configurations:

##### 1. Domestic B2B (GST-registered)
```
Name: SG B2B GST
Detect Automatically: ✅
VAT Required: ✅
Country: Singapore
Tax Mapping:
  9% SR (Sales) → 9% SR (Sales)
```

##### 2. Domestic B2C (Non-GST registered)
```
Name: SG B2C
Detect Automatically: ✅
VAT Required: ⬜ (unticked)
Country: Singapore
Tax Mapping:
  9% SR (Sales) → 9% SR (Sales)
```

**Note:** For Singapore, B2B and B2C have the same 9% GST rate, so you can combine them into one "Singapore Domestic" fiscal position.

##### 3. Export / International
```
Name: Export - Zero Rated
Detect Automatically: ✅
Country Group: NOT Singapore
Tax Mapping:
  9% SR (Sales) → ZR (0%)
```

##### 4. Reverse Charge (Imported Services)
```
Name: Reverse Charge - Imported Services
Country Group: NOT Singapore
Tax Mapping (Purchases):
  TX 9% → RC 9% (Reverse Charge)
```

#### Important Notes:
- **Customer fiscal positions** only need sales tax mappings
- **Vendor fiscal positions** only need purchase tax mappings
- Customer fiscal positions have **zero impact** on input tax calculations
- Input tax is controlled by vendor bills and purchase taxes

---

### Step 7: Reverse Charge Configuration

For imported services from overseas vendors:
- Configure RC tax to generate both tax debit and tax credit (100% / -100% split)
- Self-assessed output tax + simultaneous input tax claim
- Net zero if fully taxable business

---

### Step 8: Default Taxes on Products

**Location:** Accounting → Configuration → Settings → Taxes

Set defaults:
- **Default Sales Tax:** SR (9% Standard Rated)
- **Default Purchase Tax:** TX (9% Taxable Purchase)

For products with different treatment:
- Go to Product → Invoicing tab
- Override Sales Taxes / Purchase Taxes as needed

---

### Step 9: GST Filing Period Setup

**Location:** Accounting → Configuration → Settings → Fiscal Periods

Align to IRAS filing frequency:
- **Quarterly** for most businesses
- **Monthly** if under Import GST Deferment Scheme (IGDS) or if elected

---

### Step 10: PayNow QR Code (Optional)

**Location:** Accounting → Configuration → Settings → Customer Payments

Enable QR Codes option, then:
- Go to Contacts → Configuration → Bank Accounts
- Set Proxy Type and Proxy Value

---

### Step 11: InvoiceNow / Peppol (Mandatory from Nov 2025+)

**Effective dates:**
- **1 November 2025:** Newly incorporated companies voluntarily registering for GST within 6 months
- **1 April 2026:** All new voluntary GST registrants

**Requirements:**
- Solution must be on IMDA's accredited InvoiceNow-Ready Solution Providers (IRSP) list
- Register in SG Peppol Directory with UEN to obtain Peppol ID
- Enable GST InvoiceNow submission feature

**For CE:** Requires third-party Peppol module or Enterprise edition

---

## Fiscal Positions Explained

### The "WHO" Logic

Fiscal positions automatically handle **who** the customer/vendor is and apply appropriate tax rules.

#### Example Flow:
1. **Select customer:** Malaysian patient
2. **Odoo checks:** Country = Malaysia (not Singapore)
3. **Auto-applies:** "Export - Zero Rated" fiscal position
4. **Tax changes:** Product default SR 9% → ZR 0%
5. **Result:** Invoice without GST

### When You Need Fiscal Positions:
- Export customers (auto ZR)
- Overseas vendors (auto RC)
- Import transactions (auto IM)
- Multiple tax jurisdictions

### When You Don't Need Fiscal Positions:
- Only local Singapore customers/suppliers
- Very few transactions
- You can manually change taxes as needed

### Critical Understanding:
✅ **Fiscal positions are optional automation helpers**  
✅ **Accounting works perfectly without them**  
✅ Products with correct taxes = correct accounting  
✅ Fiscal positions just save manual tax changes  

---

## Healthcare/Nursing Home Specific GST Treatment

### Government-Subsidized Nursing Homes
- Government absorbs GST on subsidized care services
- Residents receiving subsidies don't pay GST
- MOH reimburses the absorbed GST

### Private Nursing Homes
- Must charge **9% GST** on all:
  - Care services
  - Accommodation
  - Meals provided to residents
- This is standard-rated supply (SR)

### Mixed Model (Some Subsidized + Some Private)
- Track subsidized vs private residents separately
- Subsidized: Government absorbs GST
- Private: Charge 9% GST

### Residential Property Exemption - Does NOT Apply
Nursing home accommodation is **NOT** exempt because:
- Provides composite services (accommodation + medical care + meals + nursing)
- Classified as healthcare/care services, not residential lease
- GST-registered organizations must charge GST on services

### Recommended Setup
Create fiscal position:
```
Name: Private Nursing Home Services
Tax Mapping:
  SR 9% (for private-paying residents)
  
For subsidized residents:
  Create separate product/service with ES (Exempt) 
  OR work with accountant for GST absorption mechanism
```

---

## Tax Report Availability in CE

### ⚠️ Invoicing App vs Accounting App Issue

**If you only see "Invoicing" menu (not "Accounting"):**
- You have the lightweight Invoicing app only
- Does NOT include Tax Report
- Does NOT include Chart of Accounts
- Does NOT include Journal Entries

**The "Upgrade" button leads to Enterprise Edition (paid), NOT CE upgrade!**

### What's Available in CE (with full Accounting app):

#### ✅ Generic Tax Report
**Location:** Accounting → Reporting → Tax Report

Provides:
- Summary of tax transactions by tax code
- Output tax collected (from sales)
- Input tax paid (from purchases)
- Net GST payable/claimable
- Period-based reporting

**Format example:**
```
Tax Report - Q1 2025
─────────────────────────────────
Sales Taxes:
  9% SR (Sales)      $10,000 → $900 GST
  ZR (Zero-rated)    $5,000  → $0 GST
  
Purchase Taxes:
  TX 9% (Purchase)   $3,000  → $270 GST
  IM 9% (Import)     $1,000  → $90 GST

Output Tax Total:    $900
Input Tax Total:     $360
Net GST Payable:     $540
```

### ❌ NOT Available in CE:
- GST F5 Report (IRAS format with Box 1-7)
- GST F7 Report (corrections)
- IRAS Audit File (IAF)
- Automatic Box mapping

### Manual F5 Filing Process (CE):
1. Run Tax Report in Odoo CE
2. Note figures for each tax code
3. Manually map to F5 boxes:
   - **Box 1:** Standard-rated supplies (SR sales)
   - **Box 2:** Zero-rated supplies (ZR sales)
   - **Box 5:** Total taxable purchases (TX + IM)
   - **Box 6:** Output tax (GST from SR sales)
   - **Box 7:** Input tax (GST from TX/IM purchases)
4. Log in to IRAS myTax Portal
5. Enter figures manually
6. Submit

**Time required:** 10-15 minutes per quarter for manual filing

---

## OCA Modules for Tax Reporting

### Primary Module: `account_financial_report`

**What it provides:**
- ✅ VAT/Tax Report (shows tax balances by tax code)
- ✅ General Ledger
- ✅ Trial Balance
- ✅ Aged Partner Balance
- ✅ Open Items Report
- ✅ Journal Ledger

**Availability:** Confirmed available for Odoo 18.0 branch

**Access after installation:** Invoicing → Reporting → OCA accounting reports → VAT Report

### Secondary Module: `account_tax_balance`

Foundation module for tax reporting:
- Computes tax balances within date ranges
- Used by other localization modules
- Access via: Accounting → Reporting → Taxes Balance

### Installation Methods:

#### Method 1: Manual (Recommended)
```bash
# Download from GitHub
cd /path/to/your/odoo/addons
git clone https://github.com/OCA/account-financial-reporting.git -b 18.0

# Or download ZIP:
# Go to: https://github.com/OCA/account-financial-reporting
# Select "18.0" branch
# Click Code → Download ZIP
# Extract to addons folder

# Restart Odoo
# Enable Developer Mode: Settings → Activate Developer Mode
# Apps → Update Apps List
# Search "Account Financial Report"
# Install
```

#### Method 2: Using pip
```bash
pip install odoo-addon-account-financial-report==18.0.*
```

### Alternative: Third-Party Paid Modules

**SerpentCS - Singapore GST**
- GST Form 5 and Form 7
- IAF export
- Price: ~SGD $200-300 one-time
- Available on Odoo Apps Store

**Odoo Mates - Accounting PDF Reports**
- Comprehensive reporting suite
- Financial Reports, Asset Management, Budget Management
- Price: ~$49-99
- Available on Odoo Apps Store

---

## Key Takeaways

### Accounting Automation
✅ **Products with taxes → Accounting works automatically**  
✅ Invoice posting auto-creates journal entries:
```
DEBIT:  Accounts Receivable        $1,090
CREDIT: Revenue                    $1,000
CREDIT: GST Output Tax Payable     $90
```
✅ No manual journal entries needed  
✅ Tax Report auto-populated from transactions  

### Fiscal Positions Purpose
✅ **Automate "WHO" logic** - customer/vendor location determines tax  
✅ **Optional** - accounting works without them  
✅ **Recommended for:**
- Export customers
- Overseas vendors
- Import transactions
- Multiple jurisdictions

✅ **Not needed if:**
- Only local Singapore transactions
- Low transaction volume
- Comfortable manually changing taxes

### CE Workarounds for Missing Features

**Option 1: Manual Filing (Free)**
- Use generic Tax Report
- Manually transfer to myTax Portal
- Suitable for low-volume businesses

**Option 2: OCA Modules (Free)**
- Install `account_financial_report`
- Get VAT Report and financial reports
- Better automation

**Option 3: Third-Party Modules (Paid)**
- SerpentCS, Odoo Mates, etc.
- F5/F7 automation
- IAF export
- Cost: $50-300

**Option 4: Upgrade to Enterprise (Paid)**
- Full automation
- Built-in F5/F7/IAF
- Cost: ~SGD $30-50/user/month

### Nursing Home Specific
✅ Private nursing homes: Charge 9% GST on all services  
✅ Subsidized services: Government absorbs GST (MOH reimburses)  
✅ Nursing home accommodation ≠ residential property exemption  
✅ Composite services (care + accommodation + meals) = taxable  

### Compliance Requirements
✅ Maintain records for **5 years**  
✅ File GST quarterly (or monthly if IGDS)  
✅ Submit via IRAS myTax Portal  
✅ InvoiceNow mandatory from Nov 2025/Apr 2026 (phase-in)  
✅ Keep sales/purchases listings for audit (IAF format)  

### Recommended Setup Path

**For Small Nursing Home (<100 transactions/month):**
1. Install `l10n_sg` (Singapore localization)
2. Configure company and GST registration
3. Set up products with correct taxes (SR 9%)
4. Install OCA `account_financial_report` module
5. Use VAT Report for quarterly filing
6. Manual transfer to IRAS myTax Portal
7. **Total cost: $0**

**For Medium Business (100-1000 transactions/month):**
1. Same as above, plus:
2. Set up fiscal positions for automation
3. Consider paid third-party GST module
4. **Cost: $200-300 one-time**

**For Large Business (1000+ transactions/month):**
1. Consider Odoo Enterprise
2. Full automation, IAF export, audit-ready
3. Better ROI due to time savings
4. **Cost: ~SGD $30-50/user/month**

---

## Quick Reference Commands

### Check Available Tax Codes
**Location:** Accounting → Configuration → Taxes

### View Chart of Accounts
**Location:** Accounting → Configuration → Chart of Accounts

### Create Fiscal Position
**Location:** Accounting → Configuration → Fiscal Positions → Create

### Run Tax Report
**Location:** Accounting → Reporting → Tax Report

### Install OCA Module
```bash
cd /opt/odoo/addons
git clone https://github.com/OCA/account-financial-reporting.git -b 18.0
# Restart Odoo
# Apps → Update Apps List → Install
```

---

## Additional Resources

- **IRAS GST Portal:** https://www.iras.gov.sg/taxes/goods-services-tax-(gst)
- **OCA GitHub:** https://github.com/OCA/account-financial-reporting
- **Odoo Documentation:** https://www.odoo.com/documentation/18.0/
- **IMDA InvoiceNow:** Check for accredited solution providers

---

## Document Version
- **Created:** February 18, 2026
- **Odoo Version:** 18.0 Community Edition
- **GST Rate:** 9% (current as of 2025)
- **Last Updated:** February 18, 2026

---

**End of Guide**
