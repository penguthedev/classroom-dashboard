import { Authenticated, Refine } from "@refinedev/core";
import routerBindings, {
  CatchAllNavigate,
  NavigateToResource,
  UnsavedChangesNotifier,
} from "@refinedev/react-router";
import { Outlet, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout/app-layout";
import { RESOURCES } from "@/constants";
import { authProvider } from "@/providers/auth";
import { dataProvider } from "@/providers/data";

import { LoginPage } from "@/pages/auth/login";
import { RegisterPage } from "@/pages/auth/register";
import { DashboardPage } from "@/pages/dashboard/dashboard";
import { DepartmentsListPage } from "@/pages/departments/list";
import { SubjectsListPage } from "@/pages/subjects/list";
import { ClassesListPage } from "@/pages/classes/list";
import { ClassShowPage } from "@/pages/classes/show";
import { ClassCreatePage } from "@/pages/classes/create";

function App() {
  return (
    <Refine
      dataProvider={dataProvider}
      authProvider={authProvider}
      routerProvider={routerBindings}
      resources={[
        { name: RESOURCES.departments, list: "/departments" },
        { name: RESOURCES.subjects, list: "/subjects" },
        {
          name: RESOURCES.classes,
          list: "/classes",
          show: "/classes/:id",
          create: "/classes/create",
        },
        { name: RESOURCES.users },
        { name: RESOURCES.enrollments },
      ]}
      options={{
        syncWithLocation: true,
        warnWhenUnsavedChanges: true,
        disableTelemetry: true,
      }}
    >
      <Routes>
        {/* Everything under here requires a logged-in user */}
        <Route
          element={
            <Authenticated key="protected" redirectOnFail="/login">
              <AppLayout>
                <Outlet />
              </AppLayout>
            </Authenticated>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="/departments" element={<DepartmentsListPage />} />
          <Route path="/subjects" element={<SubjectsListPage />} />
          <Route path="/classes" element={<ClassesListPage />} />
          <Route path="/classes/create" element={<ClassCreatePage />} />
          <Route path="/classes/:id" element={<ClassShowPage />} />
        </Route>

        {/* Public auth routes — bounce already-logged-in users into the app */}
        <Route
          element={
            <Authenticated key="public" fallback={<Outlet />}>
              <NavigateToResource resource="departments" />
            </Authenticated>
          }
        >
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        <Route
          path="*"
          element={<CatchAllNavigate to="/login" />}
        />
      </Routes>

      <UnsavedChangesNotifier />
    </Refine>
  );
}

export default App;
