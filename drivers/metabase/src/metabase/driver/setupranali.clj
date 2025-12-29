(ns metabase.driver.setupranali
  "SetuPranali driver for Metabase.
   Connects to SetuPranali semantic layer via REST API."
  (:require
   [clj-http.client :as http]
   [cheshire.core :as json]
   [clojure.string :as str]))

;; =============================================================================
;; Helper Functions
;; =============================================================================

(defn- base-url
  "Construct base URL from connection details."
  [{:keys [host port ssl]}]
  (str (if ssl "https" "http") "://" host ":" port))

(defn- api-request
  "Make a request to SetuPranali API."
  [method url api-key & [body]]
  (let [response (http/request
                  {:method           method
                   :url              url
                   :headers          {"X-API-Key"    api-key
                                      "Content-Type" "application/json"
                                      "Accept"       "application/json"}
                   :body             (when body (json/generate-string body))
                   :as               :json
                   :throw-exceptions false
                   :socket-timeout   30000
                   :connection-timeout 10000})]
    (if (< (:status response) 300)
      (:body response)
      (throw (ex-info (str "SetuPranali API error: " (:status response))
                      {:status (:status response)
                       :body   (:body response)})))))

;; =============================================================================
;; Connection Functions
;; =============================================================================

(defn can-connect?
  "Test if we can connect to SetuPranali."
  [details]
  (try
    (let [url (str (base-url details) "/v1/health")
          response (api-request :get url (:api-key details))]
      (= "ok" (:status response)))
    (catch Exception _
      false)))

(defn get-datasets
  "Get list of datasets from SetuPranali."
  [details]
  (let [url (str (base-url details) "/v1/introspection/datasets")
        response (api-request :get url (:api-key details))]
    (:datasets response)))

(defn get-dataset-schema
  "Get schema for a specific dataset."
  [details dataset-id]
  (let [url (str (base-url details) "/v1/introspection/datasets/" dataset-id)
        response (api-request :get url (:api-key details))]
    response))

(defn execute-query
  "Execute a query against SetuPranali."
  [details query-body]
  (let [url (str (base-url details) "/v1/query")
        response (api-request :post url (:api-key details) query-body)]
    response))

;; =============================================================================
;; Type Mapping
;; =============================================================================

(defn- setupranali-type->base-type
  "Convert SetuPranali type to Metabase base type."
  [type-str]
  (case (str/lower-case (or type-str "string"))
    "number"   :type/Number
    "integer"  :type/Integer
    "float"    :type/Float
    "decimal"  :type/Decimal
    "date"     :type/Date
    "datetime" :type/DateTime
    "timestamp" :type/DateTime
    "boolean"  :type/Boolean
    "text"     :type/Text
    :type/Text))

;; =============================================================================
;; Driver Implementation Map
;; =============================================================================

(def driver-impl
  "Map of driver implementation functions for Metabase to call."
  {:can-connect?     can-connect?
   :get-datasets     get-datasets
   :get-dataset-schema get-dataset-schema
   :execute-query    execute-query
   :type-mapping     setupranali-type->base-type})

;; =============================================================================
;; Driver Info (for plugin registration)
;; =============================================================================

(def driver-info
  {:name            "setupranali"
   :display-name    "SetuPranali"
   :description     "SetuPranali semantic layer driver"
   :connection-properties
   [{:name         "host"
     :display-name "Host"
     :placeholder  "localhost"
     :required     true}
    {:name         "port"
     :display-name "Port"
     :type         :integer
     :default      8080
     :required     true}
    {:name         "api-key"
     :display-name "API Key"
     :type         :password
     :required     true}
    {:name         "ssl"
     :display-name "Use SSL"
     :type         :boolean
     :default      false}]})

;; Print driver info when loaded
(println "SetuPranali driver loaded:" (:display-name driver-info))
