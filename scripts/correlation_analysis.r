# keep only those that actually exist (avoids 'subscript out of bounds')
fac_keep  <- intersect(facility_vars, rownames(corr))
land_keep <- intersect(land_vars,      colnames(corr))
# If nothing matches (e.g., different labels), fall back to all
if (length(fac_keep)  == 0) fac_keep  <- rownames(corr)
if (length(land_keep) == 0) land_keep <- colnames(corr)
# Subset safely
corr2 <- corr[fac_keep, land_keep, drop = FALSE]
pval2 <- pval[fac_keep, land_keep, drop = FALSE]
# --- Plot ---
library(corrplot)
colpal <- colorRampPalette(c("blue","white","red"))(200)
corrplot(
corr2,
method = "color",
type   = "full",
tl.col = "black",
tl.srt = 45,
col    = colpal,
p.mat  = pval2,
sig.level = 0.05,
insig  = "blank",
mar    = c(0,0,3,0),
title  = "Significant correlations (FDR) between facility and land-cover variables"
)
# ================================
# Batch corrplots for all blocks
# ================================
if(!require(corrplot)) install.packages("corrplot")
library(corrplot)
# --- EDIT THIS: your output folder with CSVs ---
dir_path <- "<PATH_TO_CORRELATION_MATRICES_DIR>"
# find all correlation CSVs and their matching adjusted p CSVs
corr_files <- list.files(dir_path, pattern = "_corr\\.csv$", full.names = TRUE)
padj_files <- sub("_corr\\.csv$", "_p_adj.csv", corr_files)
# keep only pairs where both files exist
pairs <- data.frame(corr = corr_files, padj = padj_files, stringsAsFactors = FALSE)
pairs <- pairs[file.exists(pairs$corr) & file.exists(pairs$padj), ]
# helper: safe name cleanup (trim spaces)
clean_names <- function(x){
x <- gsub("\\s+", " ", x)
trimws(x)
}
# color palette
colpal <- colorRampPalette(c("blue", "white", "red"))(200)
# loop over files
for(i in seq_len(nrow(pairs))){
corr_path <- pairs$corr[i]
padj_path <- pairs$padj[i]
# read as matrices
corr <- as.matrix(read.csv(corr_path, row.names = 1, check.names = FALSE))
pval <- as.matrix(read.csv(padj_path, row.names = 1, check.names = FALSE))
# align and clean dimnames
rownames(corr) <- clean_names(rownames(corr))
colnames(corr) <- clean_names(colnames(corr))
rownames(pval) <- clean_names(rownames(pval))
colnames(pval) <- clean_names(colnames(pval))
# (ensure exact same order / names)
common_rows <- intersect(rownames(corr), rownames(pval))
common_cols <- intersect(colnames(corr), colnames(pval))
corr <- corr[common_rows, common_cols, drop = FALSE]
pval <- pval[common_rows, common_cols, drop = FALSE]
# title from filename stem
stem <- sub("_corr\\.csv$", "", basename(corr_path))
plot_title <- paste0("Significant correlations (FDR) — ", stem)
# draw and save
png(file.path(dir_path, paste0(stem, "_corrplot.png")),
width = 2400, height = 1800, res = 300)
corrplot(
corr,
method    = "color",
type      = "full",
tl.col    = "black",
tl.srt    = 45,
col       = colpal,
p.mat     = pval,
sig.level = 0.05,
insig     = "blank",
mar       = c(0,0,3,0),
title     = plot_title
)
dev.off()
message("Saved: ", file.path(dir_path, paste0(stem, "_corrplot.png")))
}
message("All corrplots done.")
if(!require(openxlsx)) install.packages("openxlsx"); library(openxlsx)
dir_path <- "<PATH_TO_CORRELATION_MATRICES_DIR>"
stems <- c("RT_SO_Fa","RT_SO_LandC","RT_SO_Netw",
"RT_Fa_LandC","RT_Fa_Netw","RT_LandC_Netw")
wb <- createWorkbook()
for(stem in stems){
corr <- read.csv(file.path(dir_path, paste0(stem, "_corr.csv")), row.names=1, check.names=FALSE)
padj <- read.csv(file.path(dir_path, paste0(stem, "_p_adj.csv")), row.names=1, check.names=FALSE)
addWorksheet(wb, paste0(stem,"_corr"))
writeData(wb, paste0(stem,"_corr"), corr, rowNames=TRUE)
addWorksheet(wb, paste0(stem,"_p_adj"))
writeData(wb, paste0(stem,"_p_adj"), padj, rowNames=TRUE)
}
out_xlsx <- file.path(dir_path, "ALL_correlations_FDR.xlsx")
saveWorkbook(wb, out_xlsx, overwrite=TRUE)
message("Saved: ", out_xlsx)
# =============================================
# COMBINED 2×3 CORRPLOT FIGURE (FDR corrected)
# =============================================
# --- Install / load corrplot ---
if(!require(corrplot)) install.packages("corrplot")
library(corrplot)
# --- Folder containing your CSVs ---
dir_path <- "<PATH_TO_CORRELATION_MATRICES_DIR>"
# --- File stems (edit if needed) ---
stems <- c("RT_SO_Fa","RT_SO_LandC","RT_SO_Netw",
"RT_Fa_LandC","RT_Fa_Netw","RT_LandC_Netw")
# --- Color palette ---
colpal <- colorRampPalette(c("blue","white","red"))(200)
# --- Helper function to read each correlation + p_adj pair ---
read_pair <- function(stem){
corr_path <- file.path(dir_path, paste0(stem, "_corr.csv"))
padj_path <- file.path(dir_path, paste0(stem, "_p_adj.csv"))
corr <- as.matrix(read.csv(corr_path, row.names = 1, check.names = FALSE))
pval <- as.matrix(read.csv(padj_path, row.names = 1, check.names = FALSE))
# make sure dimensions match
rn <- intersect(rownames(corr), rownames(pval))
cn <- intersect(colnames(corr), colnames(pval))
corr <- corr[rn, cn, drop = FALSE]
pval <- pval[rn, cn, drop = FALSE]
list(corr = corr, pval = pval, title = stem)
}
pairs <- lapply(stems, read_pair)
# --- Combined figure output ---
png(file.path(dir_path, "ALL_corrplots_2x3.png"),
width = 3600, height = 2400, res = 300)
par(mfrow = c(2, 3), mar = c(0, 0, 3, 0))  # 2 rows × 3 columns grid
for (pr in pairs) {
corrplot(
pr$corr,
method = "color",
type = "full",
tl.col = "black",
tl.srt = 45,
col = colpal,
p.mat = pr$pval,
sig.level = 0.05,
insig = "blank",
mar = c(0,0,3,0),
title = paste0("Significant correlations (FDR) — ", pr$title)
)
}
dev.off()
# =============================================
# COMBINED 2×3 CORRPLOT FIGURE (FDR corrected)
# =============================================
# --- Install / load corrplot ---
if(!require(corrplot)) install.packages("corrplot")
library(corrplot)
# --- Folder containing your CSVs ---
dir_path <- "<PATH_TO_CORRELATION_MATRICES_DIR>"
# --- File stems (edit if needed) ---
stems <- c("RT_SO_Fa","RT_SO_LandC","RT_SO_Netw",
"RT_Fa_LandC","RT_Fa_Netw","RT_LandC_Netw")
# --- Color palette ---
colpal <- colorRampPalette(c("blue","white","red"))(200)
# --- Helper function to read each correlation + p_adj pair ---
read_pair <- function(stem){
corr_path <- file.path(dir_path, paste0(stem, "_corr.csv"))
padj_path <- file.path(dir_path, paste0(stem, "_p_adj.csv"))
corr <- as.matrix(read.csv(corr_path, row.names = 1, check.names = FALSE))
pval <- as.matrix(read.csv(padj_path, row.names = 1, check.names = FALSE))
# make sure dimensions match
rn <- intersect(rownames(corr), rownames(pval))
cn <- intersect(colnames(corr), colnames(pval))
corr <- corr[rn, cn, drop = FALSE]
pval <- pval[rn, cn, drop = FALSE]
list(corr = corr, pval = pval, title = stem)
}
pairs <- lapply(stems, read_pair)
# --- Combined figure output ---
png(file.path(dir_path, "ALL_corrplots_2x3.png"),
width = 3600, height = 2400, res = 300)
par(mfrow = c(2, 3), mar = c(0, 0, 3, 0))  # 2 rows × 3 columns grid
for (pr in pairs) {
corrplot(
pr$corr,
method = "color",
type = "full",
tl.col = "black",
tl.srt = 45,
col = colpal,
p.mat = pr$pval,
sig.level = 0.05,
insig = "blank",
mar = c(0,0,3,0),
title = paste0("Significant correlations (FDR) — ", pr$title)
)
}
dev.off()
# ======================================
#  FULL COMBINED CORRELATION MATRIX
# ======================================
if(!require(corrplot)) install.packages("corrplot")
library(corrplot)
# --- Load full dataset ---
data_path <- "<PATH_TO_DATASET_FILE>"
if(!require(readxl)) install.packages("readxl")
library(readxl)
df <- read_excel(data_path)
df <- as.data.frame(df)
# --- Select all numeric variables you used in the sub-analyses ---
# Adjust column ranges if your variable groups differ
df_all <- df[c(2:50)]   # socio, facility, land cover, network columns
df_all <- scale(df_all) # z-score standardization
# --- Compute correlation & adjusted p-values ---
correlation_test <- function(mat) {
n <- ncol(mat)
corr <- cor(mat, use = "pairwise.complete.obs", method = "pearson")
p.mat <- matrix(NA, n, n)
for (i in 1:n) {
for (j in 1:n) {
p.mat[i, j] <- cor.test(mat[, i], mat[, j])$p.value
}
}
p.adj <- matrix(p.adjust(p.mat, method = "fdr"), n, n)
list(corr = corr, p_adj = p.adj)
}
result <- correlation_test(df_all)
corr <- result$corr
pval <- result$p_adj
# --- Plot global corrplot ---
colpal <- colorRampPalette(c("blue", "white", "red"))(200)
png(file.path(dir_path, "FULL_Global_Corrplot.png"),
width = 3600, height = 3000, res = 300)
corrplot(
corr,
method = "color",
type = "full",
tl.col = "black",
tl.cex = 0.6,   # smaller labels
tl.srt = 45,
col = colpal,
p.mat = pval,
sig.level = 0.05,
insig = "blank",
mar = c(0,0,3,0),
title = "Global correlation matrix (FDR adjusted)"
)
# ================================
# Global correlation (robust) + corrplot
# ================================
if(!require(readxl))   install.packages("readxl")
if(!require(corrplot)) install.packages("corrplot")
library(readxl)
library(corrplot)
# ---- paths ----
data_path <- "<PATH_TO_DATASET_FILE>"
out_dir   <- "<PATH_TO_CORRELATION_MATRICES_DIR>"
out_png   <- file.path(out_dir, "FULL_Global_Corrplot.png")
# ---- load ----
df <- as.data.frame(read_excel(data_path))
# ---- keep only the columns you want (edit if needed) ----
# if your variables are in 2:50 as before:
X <- df[, 2:50, drop = FALSE]
# ---- keep numeric columns only ----
num_cols <- vapply(X, is.numeric, logical(1))
X <- X[, num_cols, drop = FALSE]
# ---- drop columns that are all NA or zero variance ----
nzv <- sapply(X, function(x) {
x_ok <- x[is.finite(x)]
if (length(x_ok) < 2) return(FALSE)
sd(x_ok, na.rm = TRUE) > 0
})
X <- X[, nzv, drop = FALSE]
# ---- make names unique (avoids collisions) ----
colnames(X) <- make.unique(colnames(X))
# ---- standardize (z-score) ----
Xz <- scale(X)
# ---- correlation & p-values (pairwise complete) ----
n <- ncol(Xz)
C <- cor(Xz, use = "pairwise.complete.obs", method = "pearson")
# p-values with identical dimnames
P <- matrix(NA_real_, n, n, dimnames = list(colnames(Xz), colnames(Xz)))
for (i in seq_len(n)) {
xi <- Xz[, i]
for (j in seq_len(n)) {
xj <- Xz[, j]
ok <- is.finite(xi) & is.finite(xj)
if (sum(ok) >= 3) {
P[i, j] <- suppressWarnings(cor.test(xi[ok], xj[ok], method = "pearson")$p.value)
}
}
}
# ---- FDR adjust; keep dimnames identical to C ----
Padj_vec <- p.adjust(as.vector(P), method = "fdr")
Padj <- matrix(Padj_vec, nrow = nrow(P), ncol = ncol(P),
dimnames = dimnames(P))
# ---- sanity checks ----
stopifnot(identical(dim(C), dim(Padj)))
stopifnot(identical(rownames(C), rownames(Padj)))
stopifnot(identical(colnames(C), colnames(Padj)))
# ---- plot ----
colpal <- colorRampPalette(c("blue", "white", "red"))(200)
png(out_png, width = 3600, height = 3000, res = 300)
corrplot(
C,
method    = "color",
type      = "full",
tl.col    = "black",
tl.cex    = 0.6,        # shrink labels for many vars
tl.srt    = 45,
col       = colpal,
p.mat     = Padj,       # FDR-adjusted p-values
sig.level = 0.05,
insig     = "blank",    # hide non-significant
mar       = c(0,0,3,0),
title     = "Global correlation matrix (FDR adjusted)"
)
dev.off()
# auto-open
browseURL(out_png)
cat("Saved:", out_png, "\nVars plotted:", ncol(Xz), "\n")
# ==========================================================
# Batch for 5 cases: Excel (corr & FDR p) + Combined 2x3 PNG + Global PNG
# ==========================================================
if(!require(readxl))   install.packages("readxl")
if(!require(corrplot)) install.packages("corrplot")
if(!require(openxlsx)) install.packages("openxlsx")
library(readxl); library(corrplot); library(openxlsx)
# ---------- helpers ----------
scale_df <- function(df){
num <- vapply(df, is.numeric, logical(1))
out <- as.data.frame(df)
out[num] <- lapply(out[num], function(x) as.numeric(scale(x)))
out
}
cor_block <- function(df1, df2, method="pearson", p_adjust="fdr"){
df1 <- as.data.frame(df1); df2 <- as.data.frame(df2)
cn1 <- colnames(df1); cn2 <- colnames(df2)
C <- cor(df1, df2, use="pairwise.complete.obs", method=method)
P <- matrix(NA_real_, nrow=length(cn1), ncol=length(cn2), dimnames=list(cn1, cn2))
for(i in seq_along(cn1)){
x <- df1[[i]]
for(j in seq_along(cn2)){
y <- df2[[j]]
ok <- is.finite(x) & is.finite(y)
P[i, j] <- if(sum(ok) >= 3) suppressWarnings(cor.test(x[ok], y[ok], method=method)$p.value) else NA_real_
}
}
P_adj <- matrix(p.adjust(as.vector(P), method=p_adjust), nrow=nrow(P), ncol=ncol(P),
dimnames=dimnames(P))
list(corr=C, p_adj=P_adj)
}
make_global_corrplot <- function(dat, col_range, out_png, title="Global correlation matrix (FDR adjusted)"){
X <- dat[, col_range, drop=FALSE]
num_cols <- vapply(X, is.numeric, logical(1))
X <- X[, num_cols, drop=FALSE]
nzv <- sapply(X, function(x){
x_ok <- x[is.finite(x)]
if(length(x_ok) < 2) return(FALSE)
sd(x_ok, na.rm=TRUE) > 0
})
X <- X[, nzv, drop=FALSE]
colnames(X) <- make.unique(colnames(X))
Xz <- scale(X)
n <- ncol(Xz)
C <- cor(Xz, use="pairwise.complete.obs", method="pearson")
P <- matrix(NA_real_, n, n, dimnames=list(colnames(Xz), colnames(Xz)))
for(i in seq_len(n)){
xi <- Xz[, i]
for(j in seq_len(n)){
xj <- Xz[, j]
ok <- is.finite(xi) & is.finite(xj)
P[i, j] <- if(sum(ok) >= 3) suppressWarnings(cor.test(xi[ok], xj[ok])$p.value) else NA_real_
}
}
Padj <- matrix(p.adjust(as.vector(P), method="fdr"), n, n, dimnames=dimnames(P))
colpal <- colorRampPalette(c("blue","white","red"))(200)
png(out_png, width=3600, height=3000, res=300)
corrplot(
C, method="color", type="full",
tl.col="black", tl.cex=0.6, tl.srt=45,
col=colpal,
p.mat=Padj, sig.level=0.05, insig="blank",
mar=c(0,0,3,0), title=title
)
dev.off()
invisible(list(C=C, P_adj=Padj))
}
write_all_matrices_xlsx <- function(wb_path, matrices_named_list){
wb <- createWorkbook()
for(nm in names(matrices_named_list)){
addWorksheet(wb, paste0(nm, "_corr"))
writeData(wb, paste0(nm, "_corr"), matrices_named_list[[nm]]$corr, rowNames=TRUE)
addWorksheet(wb, paste0(nm, "_p_adj"))
writeData(wb, paste0(nm, "_p_adj"), matrices_named_list[[nm]]$p_adj, rowNames=TRUE)
}
saveWorkbook(wb, wb_path, overwrite=TRUE)
}
run_case_corr <- function(excel_path,
out_dir,
ranges,          # list(SOS=..., FACI=..., LANDC=..., NETW=...)
sheet = 1,
make_excel = TRUE,
make_combined_png = TRUE,
make_global_png = TRUE){
if(!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)
dat <- as.data.frame(read_excel(excel_path, sheet = sheet))
# blocks
df_SOS   <- dat[ranges$SOS]
df_FACI  <- dat[ranges$FACI]
df_LANDC <- dat[ranges$LANDC]
df_NETW  <- dat[ranges$NETW]
SOS_z   <- scale_df(df_SOS)
FACI_z  <- scale_df(df_FACI)
LANDC_z <- scale_df(df_LANDC)
NETW_z  <- scale_df(df_NETW)
blocks <- list(
RT_SO_Fa       = list(A=SOS_z,   B=FACI_z,   label="SO × FACI"),
RT_SO_LandC    = list(A=SOS_z,   B=LANDC_z,  label="SO × LANDC"),
RT_SO_Netw     = list(A=SOS_z,   B=NETW_z,   label="SO × NETW"),
RT_Fa_LandC    = list(A=FACI_z,  B=LANDC_z,  label="FACI × LANDC"),
RT_Fa_Netw     = list(A=FACI_z,  B=NETW_z,   label="FACI × NETW"),
RT_LandC_Netw  = list(A=LANDC_z, B=NETW_z,   label="LANDC × NETW")
)
# compute matrices (for Excel + combined figure)
matrices_for_excel <- list()
plots_data <- list()
for(stem in names(blocks)){
res <- cor_block(blocks[[stem]]$A, blocks[[stem]]$B, p_adjust="fdr")
matrices_for_excel[[stem]] <- list(corr=res$corr, p_adj=res$p_adj)
plots_data[[stem]] <- list(C=res$corr, P=res$p_adj, title=blocks[[stem]]$label)
}
# Excel workbook (corr + p_adj + GLOBAL)
if (isTRUE(make_excel)) {
wb_path <- file.path(out_dir, "ALL_correlations_FDR.xlsx")
write_all_matrices_xlsx(wb_path, matrices_for_excel)
}
# Combined 2x3 PNG
if (isTRUE(make_combined_png)) {
colpal <- colorRampPalette(c("blue","white","red"))(200)
order_for_grid <- c("RT_SO_Fa","RT_SO_LandC","RT_SO_Netw",
"RT_Fa_LandC","RT_Fa_Netw","RT_LandC_Netw")
png(file.path(out_dir, "ALL_corrplots_2x3.png"), width=3600, height=2400, res=300)
par(mfrow=c(2,3), mar=c(0,0,3,0))
for(stem in order_for_grid){
pd <- plots_data[[stem]]
corrplot(
pd$C, method="color", type="full",
tl.col="black", tl.srt=45,
col=colpal,
p.mat=pd$P, sig.level=0.05, insig="blank",
title=paste0("Significant correlations (FDR) — ", pd$title)
)
}
dev.off()
}
# Global PNG (+ append GLOBAL to workbook)
if (isTRUE(make_global_png)) {
g <- make_global_corrplot(dat,
col_range = c(ranges$SOS, ranges$FACI, ranges$LANDC, ranges$NETW),
out_png = file.path(out_dir, "FULL_Global_Corrplot.png"),
title = "Global correlation matrix (FDR adjusted)")
if (isTRUE(make_excel)) {
wb_path <- file.path(out_dir, "ALL_correlations_FDR.xlsx")
wb <- loadWorkbook(wb_path)
addWorksheet(wb, "GLOBAL_corr"); writeData(wb, "GLOBAL_corr", g$C, rowNames=TRUE)
addWorksheet(wb, "GLOBAL_p_adj"); writeData(wb, "GLOBAL_p_adj", g$P_adj, rowNames=TRUE)
saveWorkbook(wb, wb_path, overwrite=TRUE)
}
}
}
