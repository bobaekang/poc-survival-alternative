library(jsonlite)
library(survival)

DATA_URL <- "https://" # JSON data endpoint
MOCK <- TRUE

fetch_data <- function(url) {
  content(fromJSON(url), as = "parsed")
}

fetch_fake_data <- function() {
  data <- read_json("../data.json", simplifyVector = TRUE)
  colnames(data) <- tolower(colnames(data))
  data$time <- data$stime / 365
  data$status <- data$scens == 1
  data[data$time >= 0, c("time", "status", "sex", "race")]
}

get_survival_data <- function(data, factor) {
  trt <- if (factor == "") 1 else factor
  formula <- as.formula(paste0("Surv(time, status) ~ ", trt))
  fit <- survfit(formula, data = data)

  survival <- vector("list", length(fit$surv))
  for (i in seq_len(length(fit$surv))) {
    survival[[i]] <- list(prob = fit$surv[i], time = fit$time[i])
  }

  pval <- NA

  if (factor != "") {
    survival_by_strata <- list()
    for (i in seq_len(length(fit$strata))) {
      n <- if (i == 1) 1 else cumsum(fit$strata)[i - 1]
      survival_by_strata[[names(fit$strata)[i]]] <- survival[n:cumsum(fit$strata)[i]]
    }
    survival <- survival_by_strata
    
    sdiff <- survdiff(eval(fit$call$formula), data = data)
    pval <- stats::pchisq(sdiff$chisq, length(sdiff$n) - 1, lower.tail = FALSE)
  }


  list(survival = survival, pval = pval)
}


#' Get survival analysis results
#' @get /
#' @serializer unboxedJSON
function(factor = "") {
  data <- if (MOCK) fetch_fake_data() else fetch_data(DATA_URL)
  get_survival_data(data, factor)
}
