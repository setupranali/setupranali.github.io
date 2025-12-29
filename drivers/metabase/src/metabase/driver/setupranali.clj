(ns metabase.driver.setupranali
  "SetuPranali driver for Metabase.
   Connects to SetuPranali semantic layer via REST API."
  (:require
   [clj-http.client :as http]
   [cheshire.core :as json]
   [clojure.string :as str]
   [metabase.driver :as driver]
   [metabase.driver.sql-jdbc.connection :as sql-jdbc.conn]
   [metabase.driver.sql-jdbc.execute :as sql-jdbc.execute]
   [metabase.driver.sql.query-processor :as sql.qp]
   [metabase.util :as u]
   [metabase.util.log :as log]))

;; =============================================================================
;; Driver Registration
;; =============================================================================

(driver/register! :setupranali
  :parent #{:sql-jdbc})

;; =============================================================================
;; Connection Details
;; =============================================================================

(defmethod driver/connection-properties :setupranali
  [_]
  [{:name         "host"
    :display-name "SetuPranali Host"
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
    :default      false}])

(defn- base-url
  "Construct base URL from connection details."
  [{:keys [host port ssl]}]
  (str (if ssl "https" "http") "://" host ":" port))

(defn- api-request
  "Make a request to SetuPranali API."
  [method url {:keys [api-key]} & [body]]
  (let [response (http/request
                  {:method       method
                   :url          url
                   :headers      {"X-API-Key"    api-key
                                  "Content-Type" "application/json"}
                   :body         (when body (json/generate-string body))
                   :as           :json
                   :throw-exceptions false})]
    (if (< (:status response) 300)
      (:body response)
      (throw (ex-info (str "SetuPranali API error: " (:status response))
                      {:status (:status response)
                       :body   (:body response)})))))

;; =============================================================================
;; Database Connection
;; =============================================================================

(defmethod driver/can-connect? :setupranali
  [_ details]
  (try
    (let [url (str (base-url details) "/v1/health")]
      (= "ok" (:status (api-request :get url details))))
    (catch Exception e
      (log/error e "Failed to connect to SetuPranali")
      false)))

(defmethod driver/describe-database :setupranali
  [_ database]
  (let [details (:details database)
        url     (str (base-url details) "/v1/introspection/datasets")
        response (api-request :get url details)]
    {:tables (set (for [dataset (:datasets response)]
                    {:name   (:id dataset)
                     :schema nil}))}))

(defmethod driver/describe-table :setupranali
  [_ database {:keys [name]}]
  (let [details  (:details database)
        url      (str (base-url details) "/v1/introspection/datasets/" name)
        response (api-request :get url details)
        schema   (:schema response)]
    {:name   name
     :schema nil
     :fields (set
              (concat
               ;; Dimensions
               (for [dim (:dimensions schema)]
                 {:name              (:name dim)
                  :database-type     (or (:type dim) "string")
                  :base-type         (case (:type dim)
                                       "number"  :type/Number
                                       "integer" :type/Integer
                                       "date"    :type/Date
                                       "datetime" :type/DateTime
                                       "boolean" :type/Boolean
                                       :type/Text)
                  :semantic-type     :type/Category
                  :database-position 0})
               ;; Metrics
               (for [metric (:metrics schema)]
                 {:name              (:name metric)
                  :database-type     "number"
                  :base-type         :type/Number
                  :semantic-type     :type/Quantity
                  :database-position 0})))}))

;; =============================================================================
;; Query Execution
;; =============================================================================

(defmethod driver/execute-reducible-query :setupranali
  [_ query context respond]
  (let [database  (get-in query [:database])
        details   (:details database)
        native    (get-in query [:native :query])
        dataset   (get-in query [:native :dataset] "default")]
    ;; Parse the native query to extract dataset, dimensions, metrics
    (try
      (let [query-body (if (string? native)
                         (json/parse-string native true)
                         native)
            url        (str (base-url details) "/v1/query")
            response   (api-request :post url details query-body)
            columns    (map :name (:columns response))
            rows       (map (fn [row]
                              (mapv #(get row (keyword %)) columns))
                            (:data response))]
        (respond {:cols (map (fn [col]
                               {:name col
                                :base_type :type/Text})
                             columns)}
                 rows))
      (catch Exception e
        (log/error e "Query execution failed")
        (throw e)))))

;; =============================================================================
;; SQL Generation (for simple queries via GUI)
;; =============================================================================

(defmethod sql.qp/->honeysql [:setupranali :field]
  [driver field]
  ;; Convert field reference to SetuPranali query format
  (:field-name field))

(defmethod driver/humanize-connection-error-message :setupranali
  [_ message]
  (condp re-matches message
    #".*Connection refused.*"
    "Can't connect to SetuPranali. Is the server running?"
    
    #".*401.*"
    "Invalid API key. Please check your credentials."
    
    #".*403.*"
    "Access denied. Your API key may not have permission."
    
    message))

;; =============================================================================
;; Feature Support
;; =============================================================================

(defmethod driver/database-supports? [:setupranali :foreign-keys]
  [_ _ _]
  false)

(defmethod driver/database-supports? [:setupranali :nested-queries]
  [_ _ _]
  false)

(defmethod driver/database-supports? [:setupranali :expressions]
  [_ _ _]
  false)

(defmethod driver/database-supports? [:setupranali :native-parameters]
  [_ _ _]
  true)

;; The driver supports basic aggregations through the semantic layer
(defmethod driver/database-supports? [:setupranali :basic-aggregations]
  [_ _ _]
  true)

