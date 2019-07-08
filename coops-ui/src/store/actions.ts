import axios from "@/axios-auth";

export default {
  setCorpNum({ commit }, corpNum) {
    commit("corpNum", corpNum);
  },
  setCurrentDate({ commit }, currentDate) {
    commit("currentDate", currentDate);
  },
  setLastAgmDate({ commit }, lastAgmDate) {
    commit("lastAgmDate", lastAgmDate);
  },
  setARFilingYear({ commit }, ARFilingYear) {
    commit("ARFilingYear", ARFilingYear);
  },
  setFiledDate({ commit }, filedDate) {
    commit("filedDate", filedDate);
  },
  setAgmDate({ commit }, agmDate) {
    commit("agmDate", agmDate);
  },
  setNoAGM({ commit }, noAGM) {
    commit("noAGM", noAGM);
  },
  setRegOffAddrChange({ commit }, regOffAddrChange) {
    commit("regOffAddrChange", regOffAddrChange);
  },
  setValidated({ commit }, validated) {
    commit("validated", validated);
  },
  setEntityBusinessNo({ commit }, entityBusinessNo) {
    commit("entityBusinessNo", entityBusinessNo);
  },
  setEntityName({ commit }, entityName) {
    commit("entityName", entityName);
  },
  setEntityStatus({ commit }, entityStatus) {
    commit("entityStatus", entityStatus);
  },
  setEntityIncNo({ commit }, entityIncNo) {
    commit("entityIncNo", entityIncNo);
  },

  getARInfo({ commit, state }, id) {
    if (state.corpNum) {
      // TODO - make proper axios call
      var url = state.corpNum + "/filings/" + id;
      axios
        .get(url)
        .then(response => {
          if (response && response.data) {
            const lastARJson = response.data;
            if (lastARJson && lastARJson.filing && lastARJson.filing.annualReport) {
              // TODO - do something with JSON data
              // TODO - enable filing for current year
              if (this.currentDate && this.lastAgmDate) {
                const currentYear = +this.currentDate.substring(0, 4);
                const lastAgmYear = +this.lastAgmDate.substring(0, 4);
                if (lastAgmYear < currentYear) {
                  commit("ARFilingYear", (lastAgmYear + 1).toString());
                } else {
                  // already filed for this year
                  commit("ARFilingYear", null);
                }
              }
            } else {
              console.log("setARInfo() error - invalid Annual Report");
            }
          } else {
            console.log("getARInfo() error - invalid response data");
          }
        })
        .catch(error => {
          console.error("getARInfo() error =", error);
          // TODO - delete this when API works
        });
    }
  },

  fetchEntityInfo({ commit, state }) {
    if (state.corpNum) {
      const url = state.corpNum;
      axios
        .get(url)
        .then(response => {
          if (response && response.data && response.data.business) {
            commit("entityName", response.data.business.legalName);
            commit("entityStatus", response.data.business.status);
            commit("entityBusinessNo", response.data.business.taxId);
            commit("entityIncNo", response.data.business.identifier);
            const dateInput = response.data.business.lastAnnualGeneralMeetingDate;
            if (
              dateInput &&
              dateInput.length === 10 &&
              dateInput.indexOf("-") === 4 &&
              dateInput.indexOf("-", 5) === 7 &&
              dateInput.indexOf("-", 8) === -1
            ) {
              commit("lastAgmDate", dateInput);
            } else {
              commit("lastAgmDate", null);
            }
          } else {
            console.log("getEntityInfo() error - invalid response data");
          }
        })
        .catch(error => console.error("getEntityInfo() error =", error));
    }
  }
};
